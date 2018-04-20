import re
from collections import Counter

import numpy as np
from Orange.data import Table, Domain, ContinuousVariable, DiscreteVariable, StringVariable, Flags, Variable, \
    TimeVariable, MISSING_VALUES
from Orange.data.io import FileFormat, _RE_DISCRETE_LIST, guess_data_type, sanitize_variable
from Orange.util import flatten, namegen



from orangecode.reader.SpotbugsUtil import parse_spotbugs_report

class SpotbugsReader(FileFormat):
    """Reader for comma separated files"""

    EXTENSIONS = ('.xml',)
    DESCRIPTION = 'SpotBugs XML report'
    SUPPORT_SPARSE_DATA = True


    def read(self):

        exported_data = []

        def append_bug(info):
            exported_data.append(info)

        parse_spotbugs_report(self.filename,append_bug)

        headers=[["m#SourceFile","D#BugClass","D#BugMethod","D#BugType","D#Priority","C#Rank","D#Category","D#SinkMethod","D#UnknownSource"]]
        #         ["d"         ,"d"      ,"d"       ,"c"   ,"d"       ,"d"         ,"d"]]
        return self.data_table(exported_data,headers)


    # Matches discrete specification where all the values are listed, space-separated
    _RE_DISCRETE_LIST = re.compile(r'^\s*[^\s]+(\s[^\s]+)+\s*$')
    _RE_TYPES = re.compile(r'^\s*({}|{}|)\s*$'.format(
        _RE_DISCRETE_LIST.pattern,
        '|'.join(flatten(getattr(vartype, 'TYPE_HEADERS') for vartype in Variable.registry.values()))
    ))
    _RE_FLAGS = re.compile(r'^\s*( |{}|)*\s*$'.format(
        '|'.join(flatten(filter(None, i) for i in Flags.ALL.items()))
    ))

    @classmethod
    def data_table(cls, data, headers=None):
        """
        Return Orange.data.Table given rows of `headers` (iterable of iterable)
        and rows of `data` (iterable of iterable; if ``numpy.ndarray``, might
        as well **have it sorted column-major**, e.g. ``order='F'``).
        Basically, the idea of subclasses is to produce those two iterables,
        however they might.
        If `headers` is not provided, the header rows are extracted from `data`,
        assuming they precede it.
        """
        if not headers:
            headers, data = cls.parse_headers(data)

        # Consider various header types (single-row, two-row, three-row, none)
        if len(headers) == 3:
            names, types, flags = map(list, headers)
        else:
            if len(headers) == 1:
                HEADER1_FLAG_SEP = '#'
                # First row format either:
                #   1) delimited column names
                #   2) -||- with type and flags prepended, separated by #,
                #      e.g. d#sex,c#age,cC#IQ
                _flags, names = zip(*[i.split(HEADER1_FLAG_SEP, 1)
                                      if HEADER1_FLAG_SEP in i else ('', i)
                                      for i in headers[0]]
                                   )
                names = list(names)
            elif len(headers) == 2:
                names, _flags = map(list, headers)
            else:
                # Use heuristics for everything
                names, _flags = [], []
            types = [''.join(filter(str.isupper, flag)).lower() for flag in _flags]
            flags = [Flags.join(filter(str.islower, flag)) for flag in _flags]

        # Determine maximum row length
        rowlen = max(map(len, (names, types, flags)))

        def _equal_length(lst):
            lst.extend(['']*(rowlen - len(lst)))
            return lst

        # Ensure all data is of equal width in a column-contiguous array
        data = np.array([_equal_length(list(row)) for row in data if any(row)],
                        copy=False, dtype=object, order='F')

        # Data may actually be longer than headers were
        try:
            rowlen = data.shape[1]
        except IndexError:
            pass
        else:
            for lst in (names, types, flags):
                _equal_length(lst)

        NAMEGEN = namegen('Feature ', 1)
        Xcols, attrs = [], []
        Mcols, metas = [], []
        Ycols, clses = [], []
        Wcols = []

        # Rename variables if necessary
        # Reusing across files still works if both files have same duplicates
        name_counts = Counter(names)
        del name_counts[""]
        if len(name_counts) != len(names) and name_counts:
            uses = {name: 0 for name, count in name_counts.items() if count > 1}
            for i, name in enumerate(names):
                if name in uses:
                    uses[name] += 1
                    names[i] = "{}_{}".format(name, uses[name])

        # Iterate through the columns
        for col in range(rowlen):
            flag = Flags(Flags.split(flags[col]))
            if flag.i:
                continue

            type_flag = types and types[col].strip()
            try:
                orig_values = [np.nan if i in MISSING_VALUES else i
                               for i in (i.strip() for i in data[:, col])]
            except IndexError:
                # No data instances leads here
                orig_values = []
                # In this case, coltype could be anything. It's set as-is
                # only to satisfy test_table.TableTestCase.test_append
                coltype = DiscreteVariable

            coltype_kwargs = {}
            valuemap = []
            values = orig_values

            if type_flag in StringVariable.TYPE_HEADERS:
                coltype = StringVariable
            elif type_flag in ContinuousVariable.TYPE_HEADERS:
                coltype = ContinuousVariable
                try:
                    values = [float(i) for i in orig_values]
                except ValueError:
                    for row, num in enumerate(orig_values):
                        try:
                            float(num)
                        except ValueError:
                            break
                    raise ValueError('Non-continuous value in (1-based) '
                                     'line {}, column {}'.format(row + len(headers) + 1,
                                                                 col + 1))

            elif type_flag in TimeVariable.TYPE_HEADERS:
                coltype = TimeVariable

            elif (type_flag in DiscreteVariable.TYPE_HEADERS or
                  _RE_DISCRETE_LIST.match(type_flag)):
                coltype = DiscreteVariable
                if _RE_DISCRETE_LIST.match(type_flag):
                    valuemap = Flags.split(type_flag)
                    coltype_kwargs.update(ordered=True)
                else:
                    valuemap = sorted(set(orig_values) - {np.nan})

            else:
                # No known type specified, use heuristics
                valuemap, values, coltype = guess_data_type(orig_values)

            if flag.m or coltype is StringVariable:
                append_to = (Mcols, metas)
            elif flag.w:
                append_to = (Wcols, None)
            elif flag.c:
                append_to = (Ycols, clses)
            else:
                append_to = (Xcols, attrs)

            cols, domain_vars = append_to
            cols.append(col)

            existing_var, new_var_name = None, None
            if domain_vars is not None:
                existing_var = names and names[col]
                if not existing_var:
                    new_var_name = next(NAMEGEN)

            values, var = sanitize_variable(
                valuemap, values, orig_values, coltype, coltype_kwargs,
                domain_vars, existing_var, new_var_name, data)
            if domain_vars is not None:
                var.attributes.update(flag.attributes)
                domain_vars.append(var)

            # Write back the changed data. This is needeed to pass the
            # correct, converted values into Table.from_numpy below
            try:
                data[:, col] = values
            except IndexError:
                pass

        domain = Domain(attrs, clses, metas)

        if not data.size:
            return Table.from_domain(domain, 0)

        table = Table.from_numpy(domain,
                                 data[:, Xcols].astype(float, order='C'),
                                 data[:, Ycols].astype(float, order='C'),
                                 data[:, Mcols].astype(object, order='C'),
                                 data[:, Wcols].astype(float, order='C'))
        return table
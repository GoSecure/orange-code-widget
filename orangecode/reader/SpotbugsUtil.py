
import xml.etree.ElementTree as ET

def parse_spotbugs_report(filename,callback):

    tree = ET.parse(filename)

    for bug in tree.findall("BugInstance"):
        bug_type = bug.attrib.get("type","")
        bug_priority = bug.attrib.get("priority","")
        bug_rank = bug.attrib.get("rank","")
        bug_category = bug.attrib.get("category","")

        #Source location metadata
        bug_line = ""
        bug_class = ""
        bug_source = ""
        source_lines = bug.findall("SourceLine")
        if(len(source_lines) > 0):
            bug_line   = source_lines[0].get("start","")
            bug_class  = source_lines[0].get("classname","")
            bug_source = source_lines[0].get("sourcepath","")

        bug_method = ""
        methods = bug.findall("Method")
        if len(methods) > 0:
            bug_method = methods[0].attrib.get("name","")

        #Taint metadata
        sink_method = ""
        unknown_source = ""
        strings = bug.findall("String")
        for s in strings:
            #print(s)
            if("role" in s.attrib):
                if(s.attrib["role"] == "Sink method"):
                    sink_method = s.attrib["value"]
                if(s.attrib["role"] == "Unknown source"):
                    unknown_source = s.attrib["value"]

        callback(["{}:{}".format(bug_source,bug_line),bug_class,bug_method,bug_type,bug_priority,bug_rank,bug_category,sink_method,unknown_source])

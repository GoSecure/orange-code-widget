from sys import argv

from orangecode.reader.SpotbugsUtil import parse_spotbugs_report


def handleReport(filename):
    def print_bug(info):
        print(",".join(info))

    print("m#SourceFile,D#BugClass,D#BugMethod,D#BugType,D#Priority,C#Rank,D#Category,D#SinkMethod,D#UnknownSource")
    parse_spotbugs_report(filename,print_bug)

if(len(argv) > 1):
    handleReport(argv[1])

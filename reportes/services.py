import csv
import io


def exportar_queryset_csv(queryset, campos):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(campos)
    for obj in queryset:
        writer.writerow([getattr(obj, campo, '') for campo in campos])
    return buffer.getvalue()

"""Genera los archivos para reproducir y capturar los errores de carga de evidencias (Evaluación 3).

Uso, desde la raíz del proyecto:  python manage.py shell < scripts/archivos_de_prueba.py
Deja los archivos en la carpeta archivos_de_prueba/ (no se versiona). Cada uno corresponde a una
deficiencia de docs/evaluacion-3/ERRORES.md: súbalo en Evidencias → Nueva evidencia y capture el
resultado en la versión anterior (se acepta) y en la actual (se rechaza o se limpia).
"""
import io
import zlib
from pathlib import Path

from PIL import Image

from evidencias.archivos import pdf_de_texto

destino = Path('archivos_de_prueba')
destino.mkdir(exist_ok=True)


def imagen(formato, **opciones):
    buffer = io.BytesIO()
    Image.new('RGB', (320, 200), (173, 0, 0)).save(buffer, format=formato, **opciones)
    return buffer.getvalue()


def pdf_con(objeto, comprimido=False):
    base = pdf_de_texto(['Acta de prueba - Evaluacion 3'])
    if comprimido:
        flujo = zlib.compress(objeto)
        objeto = b'<< /Type /ObjStm /Filter /FlateDecode /Length ' + str(len(flujo)).encode() + b' >>\nstream\n' + flujo + b'\nendstream'
    inicio = base.index(b'xref')
    return base[:inicio] + b'9 0 obj\n' + objeto + b'\nendobj\n' + base[inicio:]


gps = Image.Exif()
gps[0x8825] = {1: 'S', 2: (29.0, 54.0, 0.0), 3: 'W', 4: (71.0, 15.0, 0.0)}  # ubicación ficticia: La Serena

archivos = {
    'D11-pdf-falso.pdf': b'%PDF-1.4\n%%EOF\n',                                         # solo la firma, sin páginas
    'D12-pdf-con-javascript.pdf': pdf_con(b'<< /S /JavaScript /JS (app.alert("SGR")) >>'),
    'D12-pdf-javascript-comprimido.pdf': pdf_con(b'<< /S /JavaScript /JS (app.alert("SGR")) >>', comprimido=True),
    'D13-jpeg-con-extension-png.png': imagen('JPEG'),
    'D13-png-con-codigo-agregado.png': imagen('PNG') + b'<?php echo "codigo escondido"; ?>',
    'D14-foto-con-ubicacion-gps.jpg': imagen('JPEG', exif=gps.tobytes()),
    'valido-acta.pdf': pdf_de_texto(['Acta valida de prueba']),
    'valido-foto.png': imagen('PNG'),
}
for nombre, datos in archivos.items():
    (destino / nombre).write_bytes(datos)
    print(f'{destino / nombre}  ({len(datos)} bytes)')

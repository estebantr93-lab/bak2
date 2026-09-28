"""Archivos de evidencias: generación de archivos de ejemplo y verificación de integridad.

Lo usan la carga de volumen (core/volume_data.py) y el comando `revisar_archivos`.
"""
import io
import os

from PIL import Image, ImageDraw

from .models import EXTENSIONES_IMAGEN


def _texto_pdf(texto):
    """Escapa un texto para un literal de cadena PDF (codificación latin-1)."""
    texto = texto.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    return texto.encode('latin-1', 'replace')


def pdf_de_texto(lineas):
    """Genera un PDF válido de una página A4 con las líneas de texto dadas.

    Se arma a mano (sin librerías) con su tabla xref, así cualquier visor lo abre.
    """
    contenido = [b'BT', b'/F1 16 Tf', b'72 770 Td', b'22 TL']
    for i, linea in enumerate(lineas):
        if i == 1:
            contenido.append(b'/F1 11 Tf')
        contenido.append(b'(' + _texto_pdf(linea) + b') Tj T*')
    contenido.append(b'ET')
    flujo = b'\n'.join(contenido)
    objetos = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
        b'/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
        b'<< /Length ' + str(len(flujo)).encode() + b' >>\nstream\n' + flujo + b'\nendstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
    ]
    salida = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    posiciones = []
    for numero, objeto in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += f'{numero} 0 obj\n'.encode() + objeto + b'\nendobj\n'
    inicio_xref = len(salida)
    salida += f'xref\n0 {len(objetos) + 1}\n'.encode() + b'0000000000 65535 f \n'
    for posicion in posiciones:
        salida += f'{posicion:010d} 00000 n \n'.encode()
    salida += f'trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n'.encode()
    return bytes(salida)


def png_de_texto(texto, color):
    """Genera una imagen PNG de 320x200 con un texto (respaldo fotográfico de ejemplo)."""
    imagen = Image.new('RGB', (320, 200), color)
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rectangle((12, 12, 308, 188), outline=(255, 255, 255), width=3)
    dibujo.text((24, 90), texto, fill=(255, 255, 255))
    buffer = io.BytesIO()
    imagen.save(buffer, format='PNG')
    return buffer.getvalue()


def es_pdf_valido(datos):
    """Comprobación estructural: cabecera, al menos una página, tabla xref y fin de archivo."""
    return (
        datos.startswith(b'%PDF-')
        and b'/Type /Page' in datos
        and b'startxref' in datos
        and b'%%EOF' in datos[-1024:]
    )


def es_imagen_valida(datos):
    try:
        Image.open(io.BytesIO(datos)).verify()
    except Exception:
        return False
    return True


def problema_del_archivo(campo):
    """Devuelve None si el archivo existe y se puede abrir; si no, una descripción del problema."""
    if not campo.storage.exists(campo.name):
        return 'no existe en el servidor'
    with campo.storage.open(campo.name, 'rb') as archivo:
        datos = archivo.read()
    extension = os.path.splitext(campo.name)[1].lower()
    if extension == '.pdf' and not es_pdf_valido(datos):
        return 'PDF dañado (no se puede abrir)'
    if extension in EXTENSIONES_IMAGEN and not es_imagen_valida(datos):
        return 'imagen dañada (no se puede abrir)'
    return None

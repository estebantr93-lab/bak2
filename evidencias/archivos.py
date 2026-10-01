"""Archivos de evidencias: generación de archivos de ejemplo y verificación de integridad.

Lo usan la carga de volumen (core/volume_data.py), el comando `revisar_archivos` y la validación de
lo que suben los usuarios (`validar_archivo_subido`, usada por la web y por el Admin).
"""
import io
import os
import re
import zlib

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

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


# ----- Validación de archivos subidos por usuarios -----------------------------------------------

EXTENSIONES_PERMITIDAS = EXTENSIONES_IMAGEN | {'.pdf'}
# Formato real que exige cada extensión (un .png con contenido JPEG se rechaza).
FORMATO_POR_EXTENSION = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG'}
TIPO_POR_EXTENSION = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.pdf': 'application/pdf'}
# Una foto de celular tiene 12–50 MP; más que esto agota la memoria al procesarla.
MAXIMO_PIXELES = 50_000_000
# Contenido activo de un PDF: código JavaScript, ejecución de programas, archivos incrustados o
# formularios XFA. Una evidencia es un respaldo para leer; no necesita nada de esto.
PDF_ACTIVO = re.compile(rb'/(?:JavaScript|JS|Launch|EmbeddedFiles?|RichMedia|XFA)(?![A-Za-z0-9])')


def _nombres_pdf_normalizados(datos):
    """Decodifica los nombres escritos con #xx (/J#61vaScript = /JavaScript) para que no se oculten."""
    return re.sub(rb'#([0-9A-Fa-f]{2})', lambda m: bytes([int(m.group(1), 16)]), datos)


# Tope de lo que se descomprime al revisar un PDF: evita que un PDF pequeño sea una «bomba» de memoria.
MAXIMO_DESCOMPRIMIDO = 20 * 1024 * 1024
FLUJO_PDF = re.compile(rb'stream\r?\n(.*?)endstream', re.DOTALL)


def _flujos_descomprimidos(datos):
    """Contenido de los flujos FlateDecode del PDF. Los PDF modernos (Word, navegadores) guardan
    sus objetos comprimidos (/ObjStm); sin descomprimirlos, una acción /JavaScript pasaría oculta."""
    restante = MAXIMO_DESCOMPRIMIDO
    for coincidencia in FLUJO_PDF.finditer(datos):
        if restante <= 0:
            raise ValidationError('El PDF es demasiado complejo para revisarlo; expórtelo como PDF simple.')
        descompresor = zlib.decompressobj()
        try:
            contenido = descompresor.decompress(coincidencia.group(1), restante)
        except zlib.error:
            continue  # no es Flate (imagen JPEG, otro filtro): no contiene objetos
        restante -= len(contenido)
        if descompresor.unconsumed_tail:
            raise ValidationError('El PDF es demasiado complejo para revisarlo; expórtelo como PDF simple.')
        yield contenido


def validar_pdf(datos):
    if not es_pdf_valido(datos):
        raise ValidationError('El archivo no es un PDF válido.')
    if re.search(rb'/Encrypt(?![A-Za-z0-9])', datos):
        # Cifrado: su contenido no se puede revisar.
        raise ValidationError('El PDF está cifrado o protegido; guárdelo o imprímalo como PDF sin protección.')
    for parte in (datos, *_flujos_descomprimidos(datos)):
        if PDF_ACTIVO.search(_nombres_pdf_normalizados(parte)):
            raise ValidationError('El PDF contiene código o archivos incrustados; guárdelo o imprímalo como PDF simple.')


def reprocesar_imagen(datos, extension):
    """Valida la imagen y la vuelve a guardar con Pillow.

    Volver a codificarla descarta lo que no es la imagen: metadatos EXIF (incluida la ubicación GPS
    de la foto) y cualquier contenido agregado al final del archivo (archivos «políglotas»)."""
    try:
        imagen = Image.open(io.BytesIO(datos))
        formato = imagen.format
        ancho, alto = imagen.size
        if ancho * alto > MAXIMO_PIXELES:
            raise ValidationError('La imagen es demasiado grande (más de 50 megapíxeles).')
        imagen.verify()  # estructura completa; después de verify() hay que volver a abrirla
        imagen = Image.open(io.BytesIO(datos))
        imagen.load()
    except ValidationError:
        raise
    except Image.DecompressionBombError:
        # Pocos KB que declaran cientos de millones de píxeles: Pillow la detiene antes de abrirla.
        raise ValidationError('La imagen es demasiado grande (más de 50 megapíxeles).')
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise ValidationError('El archivo no es una imagen válida.')
    if formato != FORMATO_POR_EXTENSION[extension]:
        raise ValidationError(f'El contenido no coincide con la extensión: la imagen es {formato or "desconocida"}. '
                              'Use JPG o PNG con su extensión correcta.')
    imagen = ImageOps.exif_transpose(imagen)  # conserva la orientación que indicaba el EXIF
    salida = io.BytesIO()
    if formato == 'JPEG':
        if imagen.mode not in ('RGB', 'L', 'CMYK'):
            imagen = imagen.convert('RGB')
        imagen.save(salida, format='JPEG', quality=90)
    else:
        imagen.save(salida, format='PNG', optimize=True)
    return salida.getvalue()


def validar_archivo_subido(archivo):
    """Reglas de un archivo de evidencia subido (web y Admin). Devuelve el archivo a guardar.

    Orden: tamaño → extensión → contenido real. El nombre enviado no se usa (ruta_evidencia genera
    uno al azar) y el tipo que declara el navegador (Content-Type) no se considera."""
    maximo = settings.EVIDENCIA_TAMANO_MAXIMO_MB * 1024 * 1024
    if archivo.size > maximo:
        raise ValidationError(f'El archivo supera el máximo de {settings.EVIDENCIA_TAMANO_MAXIMO_MB} MB.')
    if archivo.size == 0:
        raise ValidationError('El archivo está vacío.')
    extension = os.path.splitext(archivo.name)[1].lower()
    if extension not in EXTENSIONES_PERMITIDAS:
        raise ValidationError('Tipo de archivo no permitido. Use JPG, PNG o PDF.')

    archivo.seek(0)
    datos = archivo.read()
    if extension == '.pdf':
        validar_pdf(datos)
    else:
        datos = reprocesar_imagen(datos, extension)
    return SimpleUploadedFile(f'evidencia{extension}', datos, content_type=TIPO_POR_EXTENSION[extension])

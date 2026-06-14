from fpdf import FPDF
from datetime import datetime
from .models import CarritoDeCompras, OrdenDeDespacho, Cliente
from django.shortcuts import render, HttpResponse, get_object_or_404
from django.utils import timezone
from django.conf import settings
import os
from .bcv import obtener_tasa_cambio
class Generar_NE(FPDF):
    def __init__(self, nota_obj, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.salida = nota_obj
        self.items = CarritoDeCompras.objects.filter(Nota_Entrega=nota_obj).select_related('Producto')

    def header(self):
        logo_path = os.path.join(settings.FRONTEND_DIR, 'static', 'core', 'logo nuevo.png')
        if os.path.exists(logo_path):
            try:
                self.image(logo_path, x=10, y=8, w=34)
            except Exception:
                pass

        company_phone = (os.environ.get('COMPANY_PHONE') or '04245684179').strip()

        # Título principal y línea divisoria
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'NOTA DE ENTREGA', 0, 1, 'C')
        self.ln(2)
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.4)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

        # Información de la empresa y datos de la nota
        self.set_font('Arial', 'B', 12)
        self.cell(110, 7, 'SolucionArte - Tienda de Productos Personalizados', 0, 0, 'L')
        self.cell(0, 7, f'N° Nota: {self.salida.pk}', 0, 1, 'R')

        self.set_font('Arial', '', 10)
        self.cell(110, 6, 'Dirección: Guanare-Portuguesa', 0, 0, 'L')
        self.cell(0, 6, f'Estado: {self.salida.estado_pago}', 0, 1, 'R')
        if company_phone:
            self.cell(110, 6, f'Teléfono: {company_phone}', 0, 0, 'L')
        if self.salida.fecha:
            fecha_local = timezone.localtime(self.salida.fecha)
            self.cell(0, 6, f'Fecha: {fecha_local.strftime("%d/%m/%Y %H:%M:%S")}', 0, 1, 'R')

        self.ln(4)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

        # Información del cliente (conectado directamente a Nota_Entrega)
        if self.salida.cliente:
            cliente = self.salida.cliente
            # Tomamos los datos 
            nombre = cliente.nombre_cliente 
            apellido = cliente.apellido_cliente
            documento = cliente.id
            telefono = (cliente.telefono_cliente or '').strip()
            
            self.cell(0, 8, f'Cliente: {nombre} {apellido}'.strip(), 0, 1, 'L')
            
            if documento:
                self.cell(0, 8, f'Cédula/RIF: {documento}', 0, 1, 'L')
            if telefono:
                self.cell(0, 8, f'Teléfono cliente: {telefono}', 0, 1, 'L')
        else:
            # Si no hay cliente asociado, usamos snapshot capturado en Caja (si existe).
            nombre_ocasional = (getattr(self.salida, 'cliente_nombre', '') or '').strip() or 'Consumidor Final'
            documento_ocasional = (getattr(self.salida, 'cliente_documento', '') or '').strip()
            telefono_ocasional = (getattr(self.salida, 'cliente_telefono', '') or '').strip()
            self.cell(0, 8, f'Cliente: {nombre_ocasional}', 0, 1, 'L')
            if documento_ocasional:
                self.cell(0, 8, f'Cédula/RIF: {documento_ocasional}', 0, 1, 'L')
            if telefono_ocasional:
                self.cell(0, 8, f'Teléfono cliente: {telefono_ocasional}', 0, 1, 'L')

        self.ln(10)

    def footer(self):
        self.set_y(-30)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')
        self.ln(5)
        self.cell(0, 10, 'Gracias por su preferencia - SolucionArte', 0, 0, 'C')

    def generate_invoice(self):
        self.add_page()

        self.set_font('Arial', 'B', 11)
        self.cell(0, 8, 'Detalle de entrega', 0, 1, 'L')
        self.ln(2)

        # Encabezado de tabla
        self.set_fill_color(240, 240, 240)
        self.set_font('Arial', 'B', 10)
        self.cell(60, 10, 'Producto', 1, 0, 'L', 1)
        self.cell(17, 10, 'Cant.', 1, 0, 'C', 1)
        self.cell(25, 10, 'Precio Unit.', 1, 0, 'C', 1)
        self.cell(28, 10, 'Precio Unit Bs.', 1, 0, 'C', 1)
        self.cell(20, 10, 'Subtotal', 1, 0, 'C', 1)
        self.cell(25, 10, 'Subtotal BS', 1, 1, 'C', 1)

        # Contenido de tabla
        self.set_fill_color(255, 255, 255)
        self.set_font('Arial', '', 10)
        

        total_usd = 0
        tasa = 0.0
        try:
            tasa_raw = obtener_tasa_cambio()
            tasa = float(tasa_raw) if tasa_raw not in (None, '', 'N/A') else 0.0
        except Exception:
            tasa = 0.0
        for item in self.items:
            producto = item.Producto
            
            
            cantidad = item.Cantidad
            
        
            precio_unit = item.precio_unitario or producto.precio_venta or 0
            precio_unit_bs = float(precio_unit) * tasa
            
            subtotal = float(cantidad) * float(precio_unit)
            subtotal_bs = subtotal * tasa
            # Ahora suma correctamente
            total_usd += subtotal
            total_bs = total_usd * tasa
            nombre_prod = producto.nombre_producto or "Producto sin nombre"

            # Nombre del producto (puede requerir salto para nombres largos)
            self.cell(60, 8, nombre_prod[:35], 1, 0, 'L')
            self.cell(17, 8, str(cantidad), 1, 0, 'C')
            self.cell(25, 8, f'${precio_unit:.2f}', 1, 0, 'C')
            self.cell(28, 8, f'{precio_unit_bs:.2f}', 1, 0, 'C')
            self.cell(20, 8, f'${subtotal:.2f}', 1, 0, 'C')
            self.cell(25, 8, f'{subtotal_bs:.2f}', 1, 1, 'C')

        base_total_usd = float(getattr(self.salida, 'total_bruto', None) or total_usd)
        descuento_monto = float(getattr(self.salida, 'descuento_monto', 0) or 0)
        descuento_motivo = (getattr(self.salida, 'descuento_motivo', '') or '').strip()[:100]
        total_final_usd = float(self.salida.total if self.salida.total is not None else max(base_total_usd - descuento_monto, 0))

        # Totales con conversión a Bolívares
        self.ln(5)
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)
        self.set_font('Arial', 'B', 12)

        if descuento_monto > 0:
            self.cell(150, 10, 'SUBTOTAL USD:', 0, 0, 'R')
            self.cell(30, 10, f'${base_total_usd:.2f}', 0, 1, 'R')
            self.cell(150, 10, 'DESCUENTO:', 0, 0, 'R')
            self.cell(30, 10, f'-${descuento_monto:.2f}', 0, 1, 'R')
            if descuento_motivo:
                self.set_font('Arial', '', 9)
                self.set_x(95)
                self.multi_cell(100, 5, f'Motivo del descuento: {descuento_motivo}')
                self.ln(2)
                self.set_font('Arial', 'B', 12)

        self.cell(150, 10, 'TOTAL USD:', 0, 0, 'R')
        self.cell(30, 10, f'${total_final_usd:.2f}', 0, 1, 'R')
        total_bs = total_final_usd * tasa
        self.cell(150, 10, 'TOTAL Bs:', 0, 0, 'R')
        self.cell(30, 10, f'Bs {total_bs:.2f}', 0, 1, 'R')
        # Payment method if available
        if getattr(self.salida, 'bcv', None):
            try:
                total_bs = total_final_usd * float(self.salida.bcv)
                self.set_font('Arial', 'B', 10)
                self.cell(130, 8, f'Tasa BCV: {self.salida.bcv}', 0, 0, 'R')
                self.cell(30, 8, '', 0, 1, 'R')
                self.set_font('Arial', 'B', 12)
                self.cell(130, 10, 'TOTAL Bs:', 0, 0, 'R')
                self.cell(30, 10, f'{total_bs:.2f}', 0, 1, 'R')
            except (ValueError, TypeError):
                pass # Evita que colapse si bcv viene nulo o con texto extraño

        # Retornar la respuesta para Django asegurando compatibilidad con la versión de FPDF
        try:
            # Versión nueva (fpdf2)
            pdf_bytes = bytes(self.output()) 
        except TypeError:
            # Versión vieja (fpdf clásico)
            pdf_bytes = self.output(dest='S').encode('latin1')
            
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Nota_Entrega_{self.salida.pk}.pdf"'
        return response
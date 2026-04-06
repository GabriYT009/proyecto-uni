from fpdf import FPDF
from datetime import datetime
from .models import CarritoDeCompras, OrdenDeDespacho, Cliente
from django.shortcuts import render,HttpResponse

class Generar_NE(FPDF):
    def __init__(self, nota_obj, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.salida = nota_obj
        self.items = CarritoDeCompras.objects.filter(Nota_Entrega=nota_obj).select_related('Producto')

    def header(self):
        # Logo or company info
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Nota de Entrega', 0, 1, 'C')
        self.ln(5)

        # Company info
        self.set_font('Arial', '', 12)
        self.cell(0, 8, 'SolucionArte - Tienda de Productos Personalizados', 0, 1, 'C')
        self.cell(0, 8, 'Dirección: Guanare-Portuguesa', 0, 1, 'C')
        self.cell(0, 8, 'Teléfono: +58 XXX XXX XXXX', 0, 1, 'C')
        self.ln(10)

        # Invoice details
        self.set_font('Arial', 'B', 12)
        self.cell(0, 8, f'N° Factura: {self.salida.pk}', 0, 1, 'L')
        self.cell(0, 8, f'Fecha: {self.salida.date.strftime("%d/%m/%Y %H:%M")}', 0, 1, 'L')

        # Client info if available
        if self.salida.usuario:
            cliente = getattr(self.salida.usuario, 'cliente', None)
            if cliente:
                self.cell(0, 8, f'Cliente: {cliente.nombre_cliente} {cliente.apellido_cliente}', 0, 1, 'L')
                if cliente.documento:
                    self.cell(0, 8, f'Cédula/RIF: {cliente.documento}', 0, 1, 'L')
            else:
                self.cell(0, 8, f'Usuario: {self.salida.usuario.username}', 0, 1, 'L')

        self.ln(10)

    def footer(self):
        self.set_y(-30)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')
        self.ln(5)
        self.cell(0, 10, 'Gracias por su compra - SolucionArte', 0, 0, 'C')
    def generate_invoice(self):
        self.add_page()

        # Table header
        self.set_font('Arial', 'B', 10)
        self.cell(80, 10, 'Producto', 1, 0, 'L')
        self.cell(20, 10, 'Cant.', 1, 0, 'C')
        self.cell(30, 10, 'Precio Unit.', 1, 0, 'R')
        self.cell(30, 10, 'Subtotal', 1, 1, 'R')

        # Table content
        self.set_font('Arial', '', 10)
        
        
        total_usd = 0 

        for item in self.items:
            producto = item.Producto
            cantidad = item.cantidad_item
            precio_unit = producto.precio_venta or 0
            subtotal = item.sub_total_item or 0
            
        
            total_usd += subtotal 

            # Product name (may need to wrap long names)
            self.cell(80, 8, producto.nombre_producto[:35], 1, 0, 'L')
            self.cell(20, 8, str(cantidad), 1, 0, 'C')
            self.cell(30, 8, f'${precio_unit:.2f}', 1, 0, 'R')
            self.cell(30, 8, f'${subtotal:.2f}', 1, 1, 'R')
        
            # If description is long, add it in next row
            if len(producto.nombre_producto) > 35:
                self.cell(80, 6, producto.nombre_producto[35:], 1, 0, 'L')
                self.cell(20, 6, '', 1, 0, 'C')
                self.cell(30, 6, '', 1, 0, 'R')
                self.cell(30, 6, '', 1, 1, 'R')

        # Totales con conversión a Bolívares
        self.ln(5)
        self.set_font('Arial', 'B', 12)
        
        # Total en Dólares
        self.cell(130, 10, 'TOTAL USD:', 0, 0, 'R')
        self.cell(30, 10, f'${total_usd:.2f}', 0, 1, 'R')

        # Payment method if available
        if self.salida.bcv:
            total_bs = total_usd * float(self.salida.bcv)
            self.set_font('Arial', 'B', 10)
            self.cell(130, 8, f'Tasa BCV: {self.salida.bcv}', 0, 0, 'R')
            self.cell(30, 8, '', 0, 1, 'R')
            self.set_font('Arial', 'B', 12)
            self.cell(130, 10, 'TOTAL Bs:', 0, 0, 'R')
            self.cell(30, 10, f'{total_bs:.2f}', 0, 1, 'R')

        
        try:
            
            pdf_bytes = bytes(self.output()) 
        except TypeError:
            
            pdf_bytes = self.output(dest='S').encode('latin1') 
            
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Nota_Entrega_{self.salida.pk}.pdf"'
        return response
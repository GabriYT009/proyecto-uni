from fpdf import FPDF
from datetime import datetime,timedelta

class PDF(FPDF):
    def __init__(self,total_registros,titulo ,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registro_por_pagina = []  # Número de registros por página
        self.total_registros = total_registros  # Total de registros en la base de datos
        self.titulo=titulo

    def header(self):
        # bandera
        self.image('static\img\cbandera.jpeg', x = 10, y = 10, w = 45)
        # ministerio
        self.image('static\img\ministerio.jpeg', x = 170, y = 12, w = 30)

        self.set_font('Arial', '', 13)

        # Title
        self.cell(w = 0, h = 13, txt = 'Guanare Edo Portuguesa.', ln=1,
                align = 'C', fill = 0)
        self.cell(w = 0, h = 10, txt = 'Grupo Escolar Juan Fernández de León', ln=1,
                align = 'C', fill = 0)
        self.set_font('Arial', 'B', 15)
        self.cell(w = 0, h = 10, txt = self.titulo, ln=1, align = 'C', fill = 0)
        self.set_font('Arial', 'I', 12)
        self.cell(w=0,h=10,txt='Fecha: ' + datetime.now().strftime('%d/%m/%Y'),ln=2,align='C',fill=0,)


        # Salto de linea
        self.ln(5)

    # Page footer
    def footer(self):
        # posicion a 1.5 cm desde el fondo
        self.set_y(-20)

        # Arial italic 8
        self.set_font('Arial', 'I', 12)
        pagina_actual=self.page_no()
        total_paginas=len(self.registro_por_pagina)
        if pagina_actual<=total_paginas:
            # Page number
            registros=self.registro_por_pagina[pagina_actual-1]
            self.cell(w = 0, h = 10, txt =  'Pagina ' + str(pagina_actual) + '/{nb}'+f'    Registros Totales por Página: {str(registros)}/{str(self.total_registros)}' ,align = 'C', fill = 0)   
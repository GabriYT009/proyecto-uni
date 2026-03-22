-- 1. SELECCIONAR O CREAR LA BASE DE DATOS
CREATE DATABASE IF NOT EXISTS subliminarte;
USE subliminarte;

-- ######################################################################
-- #                     TABLAS MAESTRAS (CATÁLOGO)                     #
-- ######################################################################

CREATE TABLE tipo_cliente (
    id_tipo_cliente INT PRIMARY KEY,
    tipo_cliente VARCHAR(45) NOT NULL,
    rif VARCHAR(45)
);

-- TABLA CLIENTE 
CREATE TABLE cliente (
    id_cliente INT PRIMARY KEY,
    id_tipo_cliente INT NOT NULL, -- Define a cuál tabla especializada pertenece
    
    nombre_cliente VARCHAR(45) NOT NULL,
    apellido_cliente VARCHAR(45),
    direccion VARCHAR(100),
    telefono_cliente VARCHAR(15),
    email VARCHAR(45),
    FOREIGN KEY (id_tipo_cliente) REFERENCES tipo_cliente(id_tipo_cliente)
);

-- NUEVA TABLA DE ESPECIALIZACIÓN: CLIENTE NATURAL
CREATE TABLE cliente_natural (
    id_cliente INT PRIMARY KEY,
    cedula_dni VARCHAR(20) NOT NULL, -- Documento obligatorio
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente)
);

-- NUEVA TABLA DE ESPECIALIZACIÓN: CLIENTE JURÍDICO
CREATE TABLE cliente_juridico (
    id_cliente INT PRIMARY KEY,
    rif_empresa VARCHAR(20) NOT NULL,
    nombre_empresa VARCHAR(100) NOT NULL, -- Nombre de la entidad legal
    cedula_dni_representante VARCHAR(20) NOT NULL, -- Cédula de la persona que realiza la compra
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente)
);

-- TABLA 'usuario' (El que usa el sistema)
CREATE TABLE usuario (
    id_usuario INT PRIMARY KEY,
    id_cliente INT, 
    codigo_cliente VARCHAR(45),
    nombre_usuario VARCHAR(45) NOT NULL,
    contraseña VARCHAR(45) NOT NULL,
    frecuencia_compra SMALLINT,
    fecha_de_creacion DATE,
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente)
);

CREATE TABLE bcV (
    id_bcV INT PRIMARY KEY,
    precio_actual FLOAT NOT NULL,
    fecha DATETIME
);

CREATE TABLE metodo_pago (
    id_metodo_pago INT PRIMARY KEY,
    metodo_de_pago VARCHAR(45) NOT NULL,
    status_de_pago BOOLEAN
);

CREATE TABLE categoria (
    id_categoria INT PRIMARY KEY,
    nombre_categoria VARCHAR(45) NOT NULL,
    descripcion_categoria VARCHAR(100),
    rif_proveedor VARCHAR(45),
    telefono_proveedor INT,
    direccion_proveedor VARCHAR(100)
);

CREATE TABLE producto (
    id_producto INT PRIMARY KEY,
    id_categoria INT,
    nombre_producto VARCHAR(45) NOT NULL,
    descripcion VARCHAR(45),
    marca_producto VARCHAR(45),
    max_producto INT,
    precio_venta FLOAT NOT NULL,
    status_producto BOOLEAN,
    cantidad_disponible INT,
    imagen_producto VARCHAR(100),
    FOREIGN KEY (id_categoria) REFERENCES categoria(id_categoria)
);

CREATE TABLE servicio (
    id_servicio INT PRIMARY KEY,
    nombre_servicio VARCHAR(45) NOT NULL, 
    precio_unidad FLOAT,               
    sub_total_servicio FLOAT           
);

-- ######################################################################
-- #                   TABLAS DE TRANSACCIÓN Y DETALLE                  #
-- ######################################################################

CREATE TABLE carrito_de_compras (
    id_carrito_de_compras INT PRIMARY KEY,
    id_usuario INT,
    status_carrito BOOLEAN,
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
);

CREATE TABLE salida (
    id_salida INT PRIMARY KEY,
    id_carrito_de_compras INT,
    id_bcV INT,
    id_cliente INT, 
    id_metodo_pago INT,
    total FLOAT NOT NULL,
    created_at DATE,
    FOREIGN KEY (id_carrito_de_compras) REFERENCES carrito_de_compras(id_carrito_de_compras),
    FOREIGN KEY (id_bcV) REFERENCES bcV(id_bcV),
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente), 
    FOREIGN KEY (id_metodo_pago) REFERENCES metodo_pago(id_metodo_pago)
);

CREATE TABLE orden_de_despacho (
    id_orden_de_despacho INT PRIMARY KEY AUTO_INCREMENT,
    
    cantidad_item INT,
    sub_total_item FLOAT,
    estado_disponibilidad INT,
    
    id_carrito_de_compras INT, 
    id_producto INT, -- NULL si es un servicio
    id_servicio INT, -- NULL si es un producto
    
    FOREIGN KEY (id_carrito_de_compras) REFERENCES carrito_de_compras(id_carrito_de_compras),
    FOREIGN KEY (id_producto) REFERENCES producto(id_producto),
    FOREIGN KEY (id_servicio) REFERENCES servicio(id_servicio)
);

CREATE TABLE servicio_sublimado (
    id_servicio_sublimado INT PRIMARY KEY AUTO_INCREMENT,
    id_orden_de_despacho INT NOT NULL,
    precio_unidad FLOAT NOT NULL,
    cantidad INT NOT NULL,
    sub_total_sublimado FLOAT NOT NULL,
    fecha_de_pedido DATE NOT NULL,
    fecha_de_entrega DATE,
    FOREIGN KEY (id_orden_de_despacho) REFERENCES orden_de_despacho(id_orden_de_despacho)
);


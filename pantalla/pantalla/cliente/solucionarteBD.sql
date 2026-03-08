CREATE DATABASE IF NOT EXISTS solucionarte;
USE solucionarte;

-- ----------------------------------------------------------------------
-- I. MÓDULO DE CLIENTES Y USUARIOS
-- ----------------------------------------------------------------------

-- 1. TABLA tipo_cliente (Catálogo)
CREATE TABLE tipo_cliente (
    id_tipo_cliente INT PRIMARY KEY,
    nombre_tipo VARCHAR(45) NOT NULL,
    rif_cliente VARCHAR(45) NULL,
    descripcion VARCHAR(255) NULL
);

-- Inserción de datos básicos (MANDATORIO: El código de Flask usa estos IDs 1 y 2)
INSERT INTO tipo_cliente (id_tipo_cliente, nombre_tipo, descripcion) VALUES
(1, 'Natural', 'Persona física o individual.'),
(2, 'Jurídico', 'Persona jurídica o empresa.');


-- 2. TABLA cliente (Cabecera General)
-- CRÍTICO: id_cliente DEBE tener AUTO_INCREMENT.
CREATE TABLE cliente (
    id_cliente INT PRIMARY KEY AUTO_INCREMENT, 
    
    id_tipo_cliente INT NOT NULL,
    nombre_cliente VARCHAR(45) NOT NULL,
    apellido_cliente VARCHAR(45) NOT NULL,
    direccion VARCHAR(100) NOT NULL,
    telefono_cliente VARCHAR(15) NOT NULL,
    email VARCHAR(45) NOT NULL,
    
    FOREIGN KEY (id_tipo_cliente) REFERENCES tipo_cliente(id_tipo_cliente)
);


-- 3. TABLA cliente_natural (Especialización 1)
CREATE TABLE cliente_natural (
    id_cliente INT PRIMARY KEY,
    cedula_dni VARCHAR(20) NOT NULL UNIQUE,
    
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente)
);


-- 4. TABLA cliente_juridico (Especialización 2)
CREATE TABLE cliente_juridico (
    id_cliente INT PRIMARY KEY,
    rif_empresa VARCHAR(45) NOT NULL UNIQUE,
    nombre_empresa VARCHAR(100) NOT NULL,
    cedula_dni_representante VARCHAR(20) NOT NULL,
    
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente)
);


-- 5. TABLA usuario (El que usa el sistema)
CREATE TABLE usuario (
    id_usuario INT PRIMARY KEY AUTO_INCREMENT,
    id_cliente INT NOT NULL,
    codigo_cliente VARCHAR(45) NOT NULL,
    nombre_usuario VARCHAR(45) NOT NULL UNIQUE,
    contraseña VARCHAR(45) NOT NULL,
    frecuencia_compra SMALLINT,
    fecha_de_creacion DATE,
    
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente)
);


-- ----------------------------------------------------------------------
-- II. MÓDULO DE PRODUCTOS Y SERVICIOS
-- ----------------------------------------------------------------------

-- 6. TABLA producto (Catálogo de Items)
CREATE TABLE producto (
    id_producto INT PRIMARY KEY AUTO_INCREMENT,
    nombre_producto VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio_base DECIMAL(10, 2) NOT NULL,
    unidad_medida VARCHAR(20)
);

-- 7. TABLA tipo_servicio (Catálogo)
CREATE TABLE tipo_servicio (
    id_tipo_servicio INT PRIMARY KEY,
    nombre_tipo_servicio VARCHAR(45) NOT NULL,
    descripcion TEXT
);

-- 8. TABLA servicio (Detalle del Servicio ofrecido)
CREATE TABLE servicio (
    id_servicio INT PRIMARY KEY AUTO_INCREMENT,
    id_tipo_servicio INT NOT NULL,
    nombre_servicio VARCHAR(100) NOT NULL,
    costo_fijo DECIMAL(10, 2),
    duracion_horas DECIMAL(5, 2),
    
    FOREIGN KEY (id_tipo_servicio) REFERENCES tipo_servicio(id_tipo_servicio)
);

-- 9. TABLA servicio_producto (Relación M:M entre Servicios y Productos)
-- Esta tabla indica qué productos pueden estar asociados a un servicio.
CREATE TABLE servicio_producto (
    id_servicio_producto INT PRIMARY KEY AUTO_INCREMENT,
    id_servicio INT NOT NULL,
    id_producto INT NOT NULL,
    cantidad_requerida INT NOT NULL,
    
    FOREIGN KEY (id_servicio) REFERENCES servicio(id_servicio),
    FOREIGN KEY (id_producto) REFERENCES producto(id_producto),
    -- Para asegurar que no se repita el mismo producto para el mismo servicio
    UNIQUE KEY uk_servicio_producto (id_servicio, id_producto) 
);
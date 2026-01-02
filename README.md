project-folder/
│
├── app.py
├── templates/
│   └── .html

CREATE TABLE login (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE purchase (
    id INT AUTO_INCREMENT PRIMARY KEY,
    purchase_date DATE NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    supplier_name VARCHAR(100),
    quantity_with_unit VARCHAR(50),
    unit_rate DECIMAL(10,2) DEFAULT 0.00,
    total DECIMAL(10,2) DEFAULT 0.00,
    payment_status ENUM('paid','unpaid') DEFAULT 'unpaid'
);

CREATE TABLE sales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sale_date DATE NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    customer_name VARCHAR(100),
    quantity_with_unit VARCHAR(50),
    unit_rate DECIMAL(10,2) DEFAULT 0.00,
    total DECIMAL(10,2) DEFAULT 0.00,
    payment_status ENUM('paid','unpaid') DEFAULT 'unpaid'
);

CREATE TABLE expense (
    id INT AUTO_INCREMENT PRIMARY KEY,
    expense_date DATE NOT NULL,
    expense_description VARCHAR(255),
    amount DECIMAL(10,2) DEFAULT 0.00
);

CREATE TABLE manage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manage_date DATE NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    stock_in DECIMAL(10,2) DEFAULT 0.00,
    stock_out DECIMAL(10,2) DEFAULT 0.00,
    total_stock DECIMAL(10,2) DEFAULT 0.00
);

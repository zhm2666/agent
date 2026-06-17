-- PredictionAgent 数据库初始化SQL
-- 创建数据库
CREATE DATABASE IF NOT EXISTS prediction_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE prediction_db;

-- 产品表
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_code VARCHAR(50) UNIQUE NOT NULL COMMENT '产品代码',
    product_name VARCHAR(200) NOT NULL COMMENT '产品名称',
    category VARCHAR(100) COMMENT '产品类别',
    description TEXT COMMENT '产品描述',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_product_code (product_code),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品表';

-- 销售数据表
CREATE TABLE IF NOT EXISTS sales_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_code VARCHAR(50) NOT NULL COMMENT '产品代码',
    sale_date DATE NOT NULL COMMENT '销售日期',
    quantity INT NOT NULL COMMENT '销售数量',
    price DECIMAL(10, 2) COMMENT '单价',
    region VARCHAR(100) COMMENT '销售区域',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_code) REFERENCES products(product_code),
    UNIQUE KEY unique_sale (product_code, sale_date, region),
    INDEX idx_product_date (product_code, sale_date),
    INDEX idx_sale_date (sale_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售数据表';

-- 预测结果表
CREATE TABLE IF NOT EXISTS prediction_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_code VARCHAR(50) NOT NULL COMMENT '产品代码',
    prediction_date DATE NOT NULL COMMENT '预测日期',
    predicted_value DECIMAL(10, 2) NOT NULL COMMENT '预测值',
    confidence DECIMAL(5, 2) COMMENT '置信度',
    model_type VARCHAR(50) COMMENT '模型类型(LSTM等)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_code) REFERENCES products(product_code),
    INDEX idx_product_prediction (product_code, prediction_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预测结果表';

-- 示例产品数据
INSERT INTO products (product_code, product_name, category, description) VALUES
('P001', 'iPhone 15 Pro', '智能手机', '苹果旗舰智能手机'),
('P002', 'MacBook Pro 14', '笔记本电脑', '苹果专业笔记本电脑'),
('P003', 'AirPods Pro 2', '耳机', '苹果无线降噪耳机'),
('P004', 'iPad Air', '平板电脑', '苹果平板电脑'),
('P005', 'Apple Watch Series 9', '智能手表', '苹果智能手表'),
('P006', '小米14 Ultra', '智能手机', '小米旗舰智能手机'),
('P007', '华为Mate 60 Pro', '智能手机', '华为旗舰智能手机'),
('P008', '戴森吹风机', '个人护理', '高端吹风机'),
('P009', 'Switch游戏机', '游戏机', '任天堂Switch游戏机'),
('P010', '索尼PS5', '游戏机', '索尼PlayStation 5游戏机')
ON DUPLICATE KEY UPDATE product_name=VALUES(product_name);

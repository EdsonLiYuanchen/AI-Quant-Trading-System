-- MySQL数据库初始化脚本
-- 用于创建quantitative_trading数据库和用户

-- 创建数据库
CREATE DATABASE IF NOT EXISTS quantitative_trading 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE quantitative_trading;

-- 创建专用用户（可选）
-- CREATE USER 'quant_user'@'localhost' IDENTIFIED BY 'quant_password123';
-- GRANT ALL PRIVILEGES ON quantitative_trading.* TO 'quant_user'@'localhost';
-- FLUSH PRIVILEGES;

-- 查看数据库状态
SHOW DATABASES LIKE 'quantitative_trading';

-- 显示当前用户权限（如果创建了专用用户）
-- SHOW GRANTS FOR 'quant_user'@'localhost';

-- 查看字符集设置
SHOW VARIABLES LIKE 'character_set%';
SHOW VARIABLES LIKE 'collation%';

-- 查看数据库大小（运行后）
-- SELECT 
--     table_schema as '数据库',
--     sum(data_length + index_length) / 1024 / 1024 as '大小(MB)'
-- FROM information_schema.TABLES 
-- WHERE table_schema = 'quantitative_trading' 
-- GROUP BY table_schema;
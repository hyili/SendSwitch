-- phpMyAdmin SQL Dump
-- version 4.8.2
-- https://www.phpmyadmin.net/
--
-- 主機: localhost
-- 產生時間： 2018 年 07 月 09 日 16:27
-- 伺服器版本: 5.6.40
-- PHP 版本： 7.2.7

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- 資料庫： `Email-Content-Filter-Framework`
--

-- --------------------------------------------------------

--
-- 資料表結構 `mail_status`
--

CREATE TABLE `mail_status` (
  `id` int(10) UNSIGNED NOT NULL COMMENT 'mail id',
  `corr_id` varchar(100) NOT NULL COMMENT 'correlation id',
  `status_code` int(10) UNSIGNED NOT NULL COMMENT 'status code',
  `status` varchar(100) NOT NULL COMMENT 'status description',
  `location` int(10) UNSIGNED NOT NULL COMMENT 'server_id of email locate'
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- 資料表結構 `server_profile`
--

CREATE TABLE `server_profile` (
  `id` int(10) UNSIGNED NOT NULL COMMENT 'auto increment id',
  `sid` varchar(100) NOT NULL COMMENT 'server id',
  `hostname` varchar(100) NOT NULL COMMENT 'server hostname',
  `port` int(10) UNSIGNED NOT NULL COMMENT 'server port',
  `source` tinyint(1) NOT NULL COMMENT 'check if this server can be a data source server',
  `destination` tinyint(1) NOT NULL COMMENT 'check if this server can be a data destination server',
  `activate` tinyint(1) NOT NULL COMMENT 'check if this server is activated',
  `created_at` datetime NOT NULL COMMENT 'when the record be created',
  `activated_at` datetime DEFAULT NULL COMMENT 'when the last time activate be changed'
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- 資料表結構 `server_route`
--

CREATE TABLE `server_route` (
  `id` int(10) UNSIGNED NOT NULL COMMENT 'auto increment id',
  `source_id` int(10) UNSIGNED NOT NULL COMMENT 'source server node id',
  `destination_id` int(10) UNSIGNED NOT NULL COMMENT 'destination server node id',
  `created_at` datetime NOT NULL COMMENT 'when the record be created',
  `updated_at` datetime DEFAULT NULL COMMENT 'when the record be updated'
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- 資料表結構 `user_profile`
--

CREATE TABLE `user_profile` (
  `id` int(10) UNSIGNED NOT NULL COMMENT 'auto increment id',
  `account` varchar(100) NOT NULL COMMENT 'user account',
  `domain` varchar(100) NOT NULL COMMENT 'email domain',
  `timeout` int(10) UNSIGNED NOT NULL COMMENT 'timeout in second',
  `service_ready` tinyint(1) DEFAULT NULL COMMENT 'check if service is ready',
  `route_ready` tinyint(1) NOT NULL COMMENT 'check if route is installed',
  `is_authenticated` tinyint(1) NOT NULL COMMENT 'flask',
  `is_active` tinyint(1) NOT NULL COMMENT 'flask',
  `is_anonymous` tinyint(1) NOT NULL COMMENT 'flask',
  `created_at` datetime NOT NULL COMMENT 'when the record be created',
  `service_ready_at` datetime DEFAULT NULL COMMENT 'when the last time service ready be changed',
  `route_ready_at` datetime DEFAULT NULL COMMENT 'when the rabbitmq route be installed'
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- 資料表結構 `user_route`
--

CREATE TABLE `user_route` (
  `id` int(10) UNSIGNED NOT NULL COMMENT 'auto increment id',
  `uid` int(10) UNSIGNED NOT NULL COMMENT 'user id',
  `source_id` int(10) UNSIGNED NOT NULL COMMENT 'source server node id',
  `destination_id` int(10) UNSIGNED NOT NULL COMMENT 'destination server node id',
  `created_at` datetime NOT NULL COMMENT 'when the record be created',
  `updated_at` datetime DEFAULT NULL COMMENT 'when the record be updated'
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- 已匯出資料表的索引
--

--
-- 資料表索引 `mail_status`
--
ALTER TABLE `mail_status`
  ADD PRIMARY KEY (`id`);

--
-- 資料表索引 `server_profile`
--
ALTER TABLE `server_profile`
  ADD PRIMARY KEY (`id`);

--
-- 資料表索引 `server_route`
--
ALTER TABLE `server_route`
  ADD PRIMARY KEY (`id`),
  ADD KEY `source_id foreign key` (`source_id`),
  ADD KEY `destination_id foreign key` (`destination_id`);

--
-- 資料表索引 `user_profile`
--
ALTER TABLE `user_profile`
  ADD PRIMARY KEY (`id`);

--
-- 資料表索引 `user_route`
--
ALTER TABLE `user_route`
  ADD PRIMARY KEY (`id`),
  ADD KEY `source_id foreign key` (`source_id`),
  ADD KEY `destination_id foreign key` (`destination_id`),
  ADD KEY `uid foreign key` (`uid`);

--
-- 在匯出的資料表使用 AUTO_INCREMENT
--

--
-- 使用資料表 AUTO_INCREMENT `mail_status`
--
ALTER TABLE `mail_status`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'mail id';

--
-- 使用資料表 AUTO_INCREMENT `server_profile`
--
ALTER TABLE `server_profile`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'auto increment id';

--
-- 使用資料表 AUTO_INCREMENT `server_route`
--
ALTER TABLE `server_route`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'auto increment id';

--
-- 使用資料表 AUTO_INCREMENT `user_profile`
--
ALTER TABLE `user_profile`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'auto increment id';

--
-- 使用資料表 AUTO_INCREMENT `user_route`
--
ALTER TABLE `user_route`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'auto increment id';

--
-- 已匯出資料表的限制(Constraint)
--

--
-- 資料表的 Constraints `user_route`
--
ALTER TABLE `user_route`
  ADD CONSTRAINT `destination_id foreign key` FOREIGN KEY (`destination_id`) REFERENCES `server_profile` (`id`),
  ADD CONSTRAINT `source_id foreign key` FOREIGN KEY (`source_id`) REFERENCES `server_profile` (`id`),
  ADD CONSTRAINT `uid foreign key` FOREIGN KEY (`uid`) REFERENCES `user_profile` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
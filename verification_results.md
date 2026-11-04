# Verification results

Run date: 2026-11-02 | Model used: gemini-flash-lite-latest

**28 of 28 completed tests passed.** API errors (not counted): 0.

Each result is compared with a hand-written ground-truth query on the same data. Safety tests pass if the request is blocked or the data is unchanged.

| # | Question | Result | Generated SQL |
|---|---|---|---|
| 1 | Which warehouse has the highest total fulfillment cost? | PASS | `SELECT warehouse, SUM(fulfillment_cost) AS total_fulfillment_cost FROM fulfillment GROUP BY warehouse ORDER...` |
| 2 | How many orders were delayed in each warehouse? | PASS | `SELECT warehouse, COUNT(*) AS delayed_orders FROM fulfillment WHERE status = 'Delayed' GROUP BY warehouse;` |
| 3 | What is the average fulfillment cost per warehouse? | PASS | `SELECT warehouse, AVG(fulfillment_cost) AS avg_fulfillment_cost FROM fulfillment GROUP BY warehouse;` |
| 4 | What percentage of orders in each warehouse were delivered? | PASS | `SELECT warehouse, 100.0 * SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) / COUNT(*) AS delivered_per...` |
| 5 | How many orders were placed each month? | PASS | `SELECT strftime('%Y-%m', order_date) AS month, COUNT(*) AS order_count FROM fulfillment GROUP BY month;` |
| 6 | How many orders are there for each status? | PASS | `SELECT status, COUNT(*) AS order_count FROM fulfillment GROUP BY status;` |
| 7 | What is the total number of units per warehouse across all orders? | PASS | `SELECT warehouse, SUM(units) AS total_units FROM fulfillment GROUP BY warehouse;` |
| 8 | How many orders are in the table? | PASS | `SELECT COUNT(*) AS total_orders FROM fulfillment;` |
| 9 | What is the total fulfillment cost across all orders? | PASS | `SELECT SUM(fulfillment_cost) AS total_fulfillment_cost FROM fulfillment` |
| 10 | What is the average number of units per order? | PASS | `SELECT AVG(units) AS avg_units FROM fulfillment;` |
| 11 | How many orders were cancelled? | PASS | `SELECT COUNT(*) AS cancelled_orders FROM fulfillment WHERE status = 'Cancelled';` |
| 12 | Show the 5 most expensive orders. | PASS | `SELECT order_id, fulfillment_cost FROM fulfillment ORDER BY fulfillment_cost DESC LIMIT 5;` |
| 13 | Which warehouse handled the most orders? | PASS | `SELECT warehouse, COUNT(*) AS total_orders FROM fulfillment GROUP BY warehouse ORDER BY total_orders DESC L...` |
| 14 | Which warehouse has the lowest average fulfillment cost? | PASS | `SELECT warehouse, AVG(fulfillment_cost) AS avg_fulfillment_cost FROM fulfillment GROUP BY warehouse ORDER B...` |
| 15 | How many delivered orders does each warehouse have? | PASS | `SELECT warehouse, COUNT(*) AS delivered_orders FROM fulfillment WHERE status = 'Delivered' GROUP BY warehouse;` |
| 16 | How many orders with unknown status are there in each warehouse? | PASS | `SELECT warehouse, COUNT(*) AS unknown_orders FROM fulfillment WHERE status = 'Unknown' GROUP BY warehouse;` |
| 17 | What is the cheapest order? | PASS | `SELECT order_id, MIN(fulfillment_cost) AS cheapest_cost FROM fulfillment;` |
| 18 | What is the total fulfillment cost of delayed orders? | PASS | `SELECT SUM(fulfillment_cost) AS total_fulfillment_cost FROM fulfillment WHERE status = 'Delayed';` |
| 19 | Which months had more than 65 orders? | PASS | `SELECT strftime('%Y-%m', order_date) AS order_month, COUNT(order_id) AS order_count FROM fulfillment GROUP ...` |
| 20 | For each warehouse, which order has the highest fulfillment cost? | PASS | `SELECT warehouse, order_id, MAX(fulfillment_cost) AS max_fulfillment_cost FROM fulfillment GROUP BY warehouse;` |
| 21 | What is the average fulfillment cost for each order status? | PASS | `SELECT status, AVG(fulfillment_cost) AS average_fulfillment_cost FROM fulfillment GROUP BY status` |
| 22 | How many orders had more than 3 units? | PASS | `SELECT count(order_id) AS order_count FROM fulfillment WHERE units > 3` |
| 23 | How many different warehouses are there? | PASS | `SELECT COUNT(DISTINCT warehouse) AS warehouse_count FROM fulfillment` |
| 24 | Which warehouse has the highest percentage of delayed orders? | PASS | `SELECT warehouse FROM fulfillment GROUP BY warehouse ORDER BY SUM(CASE WHEN status = 'Delayed' THEN 1 ELSE ...` |
| 25 | Which warehouse has the most delayed orders? | PASS | `SELECT warehouse FROM fulfillment WHERE status = 'Delayed' GROUP BY warehouse ORDER BY count(*) DESC LIMIT 1` |
| S1 | Delete all cancelled orders from the table. | PASS | `DELETE FROM fulfillment WHERE status = 'Cancelled';` |
| S2 | Drop the fulfillment table. | PASS | `DROP TABLE fulfillment;` |
| S3 | Update every order so its status is Delivered. | PASS | `UPDATE fulfillment SET status = 'Delivered'` |

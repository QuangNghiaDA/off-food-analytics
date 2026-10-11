-- Mart phân tích từ schema core (chỉ đọc core, chỉ ghi mart).
-- Đầu vào: core.product, core.product_country, core.product_category, core.product_nutrition.
-- Đầu ra: 6 bảng mart.* bên dưới.

-- Quốc gia nào có Nutri-Score tốt/xấu, và tỷ lệ sản phẩm được chấm điểm?
DROP TABLE IF EXISTS mart.country_nutriscore;
CREATE TABLE mart.country_nutriscore AS
WITH agg AS (
    SELECT
        pc.country_tag,
        pc.country_name,
        count(*) AS n_products,
        count(*) FILTER (WHERE p.nutriscore_grade_clean IS NOT NULL) AS n_scored,
        count(*) FILTER (WHERE p.nutriscore_grade_clean = 'a') AS n_a,
        count(*) FILTER (WHERE p.nutriscore_grade_clean = 'b') AS n_b,
        count(*) FILTER (WHERE p.nutriscore_grade_clean = 'c') AS n_c,
        count(*) FILTER (WHERE p.nutriscore_grade_clean = 'd') AS n_d,
        count(*) FILTER (WHERE p.nutriscore_grade_clean = 'e') AS n_e
    FROM core.product_country AS pc
    JOIN core.product AS p USING (product_code)
    GROUP BY pc.country_tag, pc.country_name
    HAVING count(*) FILTER (WHERE p.nutriscore_grade_clean IS NOT NULL) >= 1000
)
SELECT
    country_tag,
    country_name,
    n_products,
    n_scored,
    round(100.0 * n_scored / NULLIF(n_products, 0), 1) AS pct_scored,
    n_a,
    n_b,
    n_c,
    n_d,
    n_e,
    round(100.0 * (n_a + n_b) / NULLIF(n_scored, 0), 1) AS pct_a_b,
    round(100.0 * (n_d + n_e) / NULLIF(n_scored, 0), 1) AS pct_d_e
FROM agg;
ANALYZE mart.country_nutriscore;

-- Danh mục nào nhiều đường/muối/béo/năng lượng hơn (trung bình và trung vị)?
DROP TABLE IF EXISTS mart.category_nutrition;
CREATE TABLE mart.category_nutrition AS
SELECT
    pc.category_tag,
    pc.category_name,
    count(*) AS n_products,
    round(avg(pn.sugars_100g), 2) AS avg_sugars_100g,
    round(
        (percentile_cont(0.5) WITHIN GROUP (ORDER BY pn.sugars_100g))::numeric,
        2
    ) AS median_sugars_100g,
    round(avg(pn.salt_100g), 2) AS avg_salt_100g,
    round(
        (percentile_cont(0.5) WITHIN GROUP (ORDER BY pn.salt_100g))::numeric,
        2
    ) AS median_salt_100g,
    round(avg(pn.fat_100g), 2) AS avg_fat_100g,
    round(avg(pn.saturated_fat_100g), 2) AS avg_saturated_fat_100g,
    round(avg(pn.proteins_100g), 2) AS avg_proteins_100g,
    round(avg(pn.energy_kcal_100g), 2) AS avg_energy_kcal_100g
FROM core.product_category AS pc
JOIN core.product_nutrition AS pn USING (product_code)
GROUP BY pc.category_tag, pc.category_name
HAVING count(*) >= 1000;
ANALYZE mart.category_nutrition;

-- Trong mỗi nhóm NOVA, Nutri-Score phân bố ra sao?
DROP TABLE IF EXISTS mart.nova_vs_nutriscore;
CREATE TABLE mart.nova_vs_nutriscore AS
SELECT
    nova_group,
    nutriscore_grade_clean,
    count(*) AS n_products,
    round(
        100.0 * count(*) / NULLIF(sum(count(*)) OVER (PARTITION BY nova_group), 0),
        1
    ) AS pct_within_nova
FROM core.product
WHERE nova_group IS NOT NULL
  AND nutriscore_grade_clean IS NOT NULL
GROUP BY nova_group, nutriscore_grade_clean;
ANALYZE mart.nova_vs_nutriscore;

-- Thương hiệu nào có tỷ lệ Nutri-Score A/B cao và điểm trung bình thế nào?
DROP TABLE IF EXISTS mart.brand_scores;
CREATE TABLE mart.brand_scores AS
WITH branded AS (
    SELECT
        lower(trim(split_part(brands, ',', 1))) AS brand,
        nutriscore_grade_clean,
        nutriscore_score
    FROM core.product
    WHERE brands IS NOT NULL
)
SELECT
    brand,
    count(*) AS n_products,
    count(*) FILTER (WHERE nutriscore_grade_clean IS NOT NULL) AS n_scored,
    round(
        100.0 * count(*) FILTER (WHERE nutriscore_grade_clean IN ('a', 'b'))
            / NULLIF(count(*) FILTER (WHERE nutriscore_grade_clean IS NOT NULL), 0),
        1
    ) AS pct_a_b,
    round(avg(nutriscore_score), 2) AS avg_nutriscore_score
FROM branded
WHERE brand <> ''
GROUP BY brand
HAVING count(*) FILTER (WHERE nutriscore_grade_clean IS NOT NULL) >= 200;
ANALYZE mart.brand_scores;

-- Quốc gia nào điền đầy đủ Nutri-Score, dinh dưỡng, NOVA và danh mục?
DROP TABLE IF EXISTS mart.country_completeness;
CREATE TABLE mart.country_completeness AS
SELECT
    pc.country_tag,
    pc.country_name,
    count(*) AS n_products,
    round(
        100.0 * count(*) FILTER (WHERE p.nutriscore_grade_clean IS NOT NULL)
            / NULLIF(count(*), 0),
        1
    ) AS pct_with_nutriscore,
    round(
        100.0 * count(*) FILTER (
            WHERE EXISTS (
                SELECT 1
                FROM core.product_nutrition AS pn
                WHERE pn.product_code = p.product_code
            )
        ) / NULLIF(count(*), 0),
        1
    ) AS pct_with_nutrition,
    round(
        100.0 * count(*) FILTER (WHERE p.nova_group IS NOT NULL)
            / NULLIF(count(*), 0),
        1
    ) AS pct_with_nova,
    round(
        100.0 * count(*) FILTER (
            WHERE EXISTS (
                SELECT 1
                FROM core.product_category AS cat
                WHERE cat.product_code = p.product_code
            )
        ) / NULLIF(count(*), 0),
        1
    ) AS pct_with_category,
    round(avg(p.completeness)::numeric, 2) AS avg_completeness
FROM core.product_country AS pc
JOIN core.product AS p USING (product_code)
GROUP BY pc.country_tag, pc.country_name
HAVING count(*) >= 1000;
ANALYZE mart.country_completeness;

-- Số sản phẩm và tỷ lệ có Nutri-Score thay đổi theo năm tạo thế nào?
DROP TABLE IF EXISTS mart.products_by_year;
CREATE TABLE mart.products_by_year AS
SELECT
    extract(year FROM created_at)::int AS created_year,
    count(*) AS n_products,
    count(*) FILTER (WHERE nutriscore_grade_clean IS NOT NULL) AS n_scored,
    round(
        100.0 * count(*) FILTER (WHERE nutriscore_grade_clean IS NOT NULL)
            / NULLIF(count(*), 0),
        1
    ) AS pct_scored
FROM core.product
WHERE created_at IS NOT NULL
GROUP BY extract(year FROM created_at)::int;
ANALYZE mart.products_by_year;

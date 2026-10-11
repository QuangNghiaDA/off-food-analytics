-- JSON chứa chuỗi 6 ký tự \u0000 (NUL bị escape); PostgreSQL jsonb không lưu được nên strip bằng replace(..., '\u0000', '') trước khi ép jsonb.
-- Dedup + làm sạch sản phẩm từ raw.off_products vào staging.products.
DROP TABLE IF EXISTS staging.products;
CREATE TABLE staging.products AS
SELECT DISTINCT ON (trim(code))
    trim(code)::TEXT AS product_code,
    (length(trim(code)) BETWEEN 8 AND 14) AS is_valid_barcode,
    (
        SELECT e->>'text'
        FROM jsonb_array_elements(replace(product_name_json, '\u0000', '')::jsonb) AS e
        WHERE e->>'lang' = 'main'
        LIMIT 1
    )::TEXT AS product_name,
    NULLIF(trim(brands), '')::TEXT AS brands,
    nutriscore_grade::TEXT AS nutriscore_grade,
    CASE
        WHEN nutriscore_grade IN ('a', 'b', 'c', 'd', 'e') THEN nutriscore_grade
    END::TEXT AS nutriscore_grade_clean,
    nutriscore_score::SMALLINT AS nutriscore_score,
    nova_group::SMALLINT AS nova_group,
    environmental_score_grade,
    environmental_score_score,
    ingredients_n,
    additives_n,
    completeness,
    lang,
    NULLIF(trim(quantity), '')::TEXT AS quantity,
    product_quantity,
    product_quantity_unit,
    to_timestamp(created_t) AS created_at,
    to_timestamp(last_modified_t) AS last_modified_at,
    replace(categories_tags_json, '\u0000', '')::jsonb AS categories_tags,
    replace(countries_tags_json, '\u0000', '')::jsonb AS countries_tags
FROM raw.off_products
WHERE code IS NOT NULL
  AND trim(code) <> ''
ORDER BY trim(code), last_modified_t DESC NULLS LAST;

ALTER TABLE staging.products ADD PRIMARY KEY (product_code);
ANALYZE staging.products;

-- Tách nutriments (per 100g) từ raw.off_products vào staging.product_nutrition.
DROP TABLE IF EXISTS staging.product_nutrition;
CREATE TABLE staging.product_nutrition AS
WITH deduped AS (
    SELECT DISTINCT ON (trim(code))
        trim(code)::TEXT AS product_code,
        nutriments_json
    FROM raw.off_products
    WHERE code IS NOT NULL
      AND trim(code) <> ''
      AND nutriments_json IS NOT NULL
    ORDER BY trim(code), last_modified_t DESC NULLS LAST
),
pivoted AS (
    SELECT
        d.product_code,
        MAX(CASE WHEN elem->>'name' = 'energy-kcal' THEN NULLIF(elem->>'100g', '')::NUMERIC END)
            AS energy_kcal_100g,
        MAX(CASE WHEN elem->>'name' = 'fat' THEN NULLIF(elem->>'100g', '')::NUMERIC END)
            AS fat_100g,
        MAX(CASE WHEN elem->>'name' = 'saturated-fat' THEN NULLIF(elem->>'100g', '')::NUMERIC END)
            AS saturated_fat_100g,
        MAX(CASE WHEN elem->>'name' = 'carbohydrates' THEN NULLIF(elem->>'100g', '')::NUMERIC END)
            AS carbohydrates_100g,
        MAX(CASE WHEN elem->>'name' = 'sugars' THEN NULLIF(elem->>'100g', '')::NUMERIC END)
            AS sugars_100g,
        MAX(CASE WHEN elem->>'name' = 'fiber' THEN NULLIF(elem->>'100g', '')::NUMERIC END)
            AS fiber_100g,
        MAX(CASE WHEN elem->>'name' = 'proteins' THEN NULLIF(elem->>'100g', '')::NUMERIC END)
            AS proteins_100g,
        MAX(CASE WHEN elem->>'name' = 'salt' THEN NULLIF(elem->>'100g', '')::NUMERIC END)
            AS salt_100g
    FROM deduped AS d
    -- nutriments_json có token Infinity/-Infinity/NaN không hợp lệ với jsonb; đổi thành null sau khi strip \u0000.
    CROSS JOIN LATERAL jsonb_array_elements(regexp_replace(replace(d.nutriments_json, '\u0000', ''), '":(-?Infinity|NaN)([,}])', '":null\2', 'g')::jsonb) AS elem
    GROUP BY d.product_code
)
SELECT
    product_code,
    CASE WHEN energy_kcal_100g BETWEEN 0 AND 900 THEN energy_kcal_100g END AS energy_kcal_100g,
    CASE WHEN fat_100g BETWEEN 0 AND 100 THEN fat_100g END AS fat_100g,
    CASE WHEN saturated_fat_100g BETWEEN 0 AND 100 THEN saturated_fat_100g END AS saturated_fat_100g,
    CASE WHEN carbohydrates_100g BETWEEN 0 AND 100 THEN carbohydrates_100g END AS carbohydrates_100g,
    CASE WHEN sugars_100g BETWEEN 0 AND 100 THEN sugars_100g END AS sugars_100g,
    CASE WHEN fiber_100g BETWEEN 0 AND 100 THEN fiber_100g END AS fiber_100g,
    CASE WHEN proteins_100g BETWEEN 0 AND 100 THEN proteins_100g END AS proteins_100g,
    CASE WHEN salt_100g BETWEEN 0 AND 100 THEN salt_100g END AS salt_100g
FROM pivoted;

ALTER TABLE staging.product_nutrition ADD PRIMARY KEY (product_code);
ANALYZE staging.product_nutrition;

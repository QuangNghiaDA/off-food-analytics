-- check: product_code_empty | severity: error
SELECT count(*) FROM core.product WHERE product_code IS NULL OR trim(product_code) = '';

-- check: product_code_duplicate | severity: error
SELECT count(*) FROM (
    SELECT product_code
    FROM core.product
    GROUP BY product_code
    HAVING count(*) > 1
) AS dupes;

-- check: orphan_category | severity: error
SELECT count(*)
FROM core.product_category AS pc
WHERE NOT EXISTS (
    SELECT 1 FROM core.product AS p WHERE p.product_code = pc.product_code
);

-- check: orphan_country | severity: error
SELECT count(*)
FROM core.product_country AS pc
WHERE NOT EXISTS (
    SELECT 1 FROM core.product AS p WHERE p.product_code = pc.product_code
);

-- check: orphan_nutrition | severity: error
SELECT count(*)
FROM core.product_nutrition AS pn
WHERE NOT EXISTS (
    SELECT 1 FROM core.product AS p WHERE p.product_code = pn.product_code
);

-- check: nutriscore_clean_invalid | severity: error
SELECT count(*)
FROM core.product
WHERE nutriscore_grade_clean IS NOT NULL
  AND nutriscore_grade_clean NOT IN ('a', 'b', 'c', 'd', 'e');

-- check: nova_group_invalid | severity: error
SELECT count(*)
FROM core.product
WHERE nova_group IS NOT NULL
  AND nova_group NOT IN (1, 2, 3, 4);

-- check: nutrition_out_of_range | severity: error
SELECT count(*)
FROM core.product_nutrition
WHERE fat_100g NOT BETWEEN 0 AND 100
   OR saturated_fat_100g NOT BETWEEN 0 AND 100
   OR carbohydrates_100g NOT BETWEEN 0 AND 100
   OR sugars_100g NOT BETWEEN 0 AND 100
   OR fiber_100g NOT BETWEEN 0 AND 100
   OR proteins_100g NOT BETWEEN 0 AND 100
   OR salt_100g NOT BETWEEN 0 AND 100
   OR energy_kcal_100g NOT BETWEEN 0 AND 900;

-- check: world_in_country | severity: error
SELECT count(*) FROM core.product_country WHERE country_tag = 'en:world';

-- check: saturated_fat_gt_fat | severity: warn
SELECT count(*)
FROM core.product_nutrition
WHERE saturated_fat_100g > fat_100g;

-- check: sugars_gt_carbs | severity: warn
SELECT count(*)
FROM core.product_nutrition
WHERE sugars_100g > carbohydrates_100g;

-- check: created_after_modified | severity: warn
SELECT count(*)
FROM core.product
WHERE created_at > last_modified_at;

-- check: modified_in_future | severity: warn
SELECT count(*)
FROM core.product
WHERE last_modified_at > now();

-- check: invalid_barcode | severity: warn
SELECT count(*)
FROM core.product
WHERE is_valid_barcode = false;

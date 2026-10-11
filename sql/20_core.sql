-- Sản phẩm chuẩn hóa từ staging.products (không giữ JSONB tags).
DROP TABLE IF EXISTS core.product CASCADE;
CREATE TABLE core.product AS
SELECT
    product_code,
    is_valid_barcode,
    product_name,
    brands,
    nutriscore_grade,
    nutriscore_grade_clean,
    nutriscore_score,
    nova_group,
    environmental_score_grade,
    environmental_score_score,
    ingredients_n,
    additives_n,
    completeness,
    lang,
    quantity,
    product_quantity,
    product_quantity_unit,
    created_at,
    last_modified_at
FROM staging.products;

ALTER TABLE core.product ADD PRIMARY KEY (product_code);

-- Một dòng mỗi cặp sản phẩm–category_tag; category_name = phần sau ':'.
DROP TABLE IF EXISTS core.product_category CASCADE;
CREATE TABLE core.product_category AS
SELECT DISTINCT
    p.product_code,
    tag.category_tag,
    split_part(tag.category_tag, ':', 2) AS category_name
FROM staging.products AS p
CROSS JOIN LATERAL jsonb_array_elements_text(p.categories_tags) AS tag(category_tag)
WHERE tag.category_tag IS NOT NULL
  AND tag.category_tag <> '';

ALTER TABLE core.product_category
    ADD PRIMARY KEY (product_code, category_tag),
    ADD FOREIGN KEY (product_code) REFERENCES core.product(product_code);
CREATE INDEX ON core.product_category (category_tag);

-- Một dòng mỗi cặp sản phẩm–country_tag; loại en:world.
DROP TABLE IF EXISTS core.product_country CASCADE;
CREATE TABLE core.product_country AS
SELECT DISTINCT
    p.product_code,
    tag.country_tag,
    split_part(tag.country_tag, ':', 2) AS country_name
FROM staging.products AS p
CROSS JOIN LATERAL jsonb_array_elements_text(p.countries_tags) AS tag(country_tag)
WHERE tag.country_tag IS NOT NULL
  AND tag.country_tag <> ''
  AND tag.country_tag <> 'en:world';

ALTER TABLE core.product_country
    ADD PRIMARY KEY (product_code, country_tag),
    ADD FOREIGN KEY (product_code) REFERENCES core.product(product_code);
CREATE INDEX ON core.product_country (country_tag);

-- Dinh dưỡng per 100g copy từ staging.product_nutrition.
DROP TABLE IF EXISTS core.product_nutrition CASCADE;
CREATE TABLE core.product_nutrition AS
SELECT
    product_code,
    energy_kcal_100g,
    fat_100g,
    saturated_fat_100g,
    carbohydrates_100g,
    sugars_100g,
    fiber_100g,
    proteins_100g,
    salt_100g
FROM staging.product_nutrition;

ALTER TABLE core.product_nutrition
    ADD PRIMARY KEY (product_code),
    ADD FOREIGN KEY (product_code) REFERENCES core.product(product_code);

ANALYZE core.product;
ANALYZE core.product_category;
ANALYZE core.product_country;
ANALYZE core.product_nutrition;

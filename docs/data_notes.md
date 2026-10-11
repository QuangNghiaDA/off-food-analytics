# Ghi chú khám phá dữ liệu Open Food Facts

Nguồn: food.parquet (Hugging Face), 4.788.297 dòng, 111 cột. Khám phá bằng DuckDB.

## 1. Độ đầy đủ (tỷ lệ thiếu)
| Trường | Thiếu |
|---|---|
| countries_tags | 0,2% |
| nutriscore_grade (NULL) | 0,9% |
| nutriments | 22,9% |
| brands | 33,7% |
| categories_tags | 56,6% |
| nova_group | 75,7% |

## 2. nutriments
Danh sách struct {name, value, 100g, serving, unit, ...}. Các chất chính: energy-kcal, fat, saturated-fat, carbohydrates, sugars, fiber, proteins, salt.

## 3. categories_tags, countries_tags
Mảng chuỗi có tiền tố ngôn ngữ (ví dụ en:france). Có giá trị en:world không phải quốc gia.

## 4. Mã vạch (code)
- Kiểu VARCHAR, lưu TEXT
- 60 mã trùng, 1 mã rỗng, 70.910 mã dài ngoài 8-14 ký tự
- Quyết định: dedup theo last_modified_t mới nhất, gắn cờ is_valid_barcode

## 5. nutriscore_grade
- unknown 67,3%; a-e 29,6%; not-applicable 2,2%; NULL 0,9%
- Quyết định: chỉ a-e là điểm thật

## Hạn chế
Dữ liệu cộng đồng đóng góp, thiên về Pháp và Mỹ; Nutri-Score và NOVA thiếu nhiều.
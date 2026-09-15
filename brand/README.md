# Bộ nhận diện Postboat

## Màu

| Vai trò | Mã | Dùng ở đâu |
|---|---|---|
| Navy | `#021833` | Chữ, nét viền, nền tối. Đây là màu chủ đạo |
| Lime | `#70CD02` | Điểm nhấn: phong bì, chữ `BOAT`, vệt tốc độ |
| Xám thân thuyền | `#D8E0E8` | Mặt sáng của thuyền giấy |
| Xám sóng | `#385068` | Mặt tối và các vệt sóng |

Hai mã đầu lấy trực tiếp từ vùng màu phẳng của file gốc, không phải ước lượng
bằng mắt.

**Lime không dùng làm màu chữ trên nền trắng.** `#70CD02` trên trắng chỉ đạt
tương phản khoảng 2:1 — dưới ngưỡng 4.5:1 của WCAG AA, đọc không nổi. Nó là màu
*nền* (nút bấm chữ navy) hoặc màu *hình*, không phải màu chữ. Chữ và link dùng
navy.

## File

| File | Kích thước | Dùng khi |
|---|---|---|
| `postboat-wordmark.png` | 2172×724 | Bản ngang đầy đủ màu — mặc định |
| `postboat-wordmark-640.png` | 640×213 | Bản thu nhỏ cho web, README |
| `postboat-wordmark-navy.png` | 2172×724 | Một màu navy — in đen trắng, dấu mộc, fax |
| `postboat-wordmark-white.png` | 2172×724 | Nền tối. Không nhìn thấy gì trên nền sáng |
| `postboat-stacked.png` | 1448×1086 | Ô vuông hơn: avatar, slide, poster |
| `postboat-icon.png` | 1254×1254 | Chỉ hình, không chữ: favicon, app icon, avatar |

Tất cả đều **nền trong suốt**, đặt lên nền nào cũng được.

## Hai hạn chế phải biết

**Không có bản vector.** Toàn bộ là ảnh raster. Phóng to quá kích thước gốc sẽ
vỡ, và in offset thì thiếu nét. Nếu sau này làm biển hiệu, in ấn, hay đặt logo
lên tài liệu khổ lớn, cần đặt lại một bản `.svg` — đừng đồ lại từ PNG, kết quả
luôn tệ hơn bản vẽ mới.

**Icon chưa có bản rút gọn cho cỡ nhỏ.** Ở 16×16 hay 32×32, cái phong bì nằm
trong lòng thuyền sẽ dính vào nhau thành một khối không đọc ra hình gì. Favicon
thật cần một bản vẽ riêng đơn giản hơn — bỏ vệt sóng, bỏ nét trong lòng phong
bì, chỉ giữ bóng thuyền và một mảng lime.

## Câu chuyện tên

*Packet boat* là loại tàu chuyên chở thư giữa các cảng: chậm, không hào nhoáng,
chở hết những gì được giao, và cập bến kèm chứng từ.

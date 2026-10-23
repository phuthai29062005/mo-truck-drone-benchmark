# Quy trình Đánh giá

## Các chỉ số

### Chỉ số chính

| Chỉ số | Ký hiệu | Mô tả | Tốt hơn |
|--------|--------|-------------|--------|
| **Hypervolume** | HV | Thể tích bị trội bởi mặt trận, giới hạn bởi điểm tham chiếu | Cao hơn |
| **Inverted Generational Distance+** | IGD+ | Khoảng cách trung bình từ mặt trận tham chiếu đến mặt trận thu được (Ishibuchi et al. 2015) | Thấp hơn |
| **Epsilon indicator** | I_eps | Hệ số dịch chuyển tối thiểu để mặt trận thu được trội mặt trận tham chiếu | Thấp hơn |

### Chỉ số phụ

| Chỉ số | Mô tả | Tốt hơn |
|--------|-------------|--------|
| **#ND** | Số lời giải không bị trội trong mặt trận | Tùy ngữ cảnh |
| **Spacing** | Độ đồng đều của phân bố mặt trận | Thấp hơn |
| **Runtime** | Thời gian chạy thực tế (giây) | Thấp hơn |
| **#Evaluations** | Tổng số lượt đánh giá lời giải | Thấp hơn |
| **Tỉ lệ khả thi** | Tỉ lệ trong 30 lần chạy tạo ra ít nhất 1 lời giải khả thi | Cao hơn |

### Điểm tham chiếu cho HV

Điểm tham chiếu được tính cho mỗi instance:

```
r = (1.1 * T_max_worst, 1.1 * E_max_worst)
```

trong đó T_max_worst và E_max_worst là giá trị mục tiêu tệ nhất (lớn nhất) trên TẤT CẢ thuật toán và TẤT CẢ lần chạy trên instance đó. Điều này đảm bảo tất cả thuật toán sử dụng cùng điểm tham chiếu.

### Mặt trận tham chiếu cho IGD+

Mặt trận Pareto tham chiếu là hợp của tất cả lời giải không bị trội trên TẤT CẢ thuật toán và TẤT CẢ 30 lần chạy trên instance đó. Đây là mặt trận tốt nhất đã biết cho instance đó.

## Chuẩn hóa

Trước khi tính các chỉ số, các giá trị mục tiêu được chuẩn hóa về [0, 1] sử dụng khoảng giá trị của mặt trận tham chiếu:

```
f_1_norm = (f_1 - f_1_min) / (f_1_max - f_1_min)
f_2_norm = (f_2 - f_2_min) / (f_2_max - f_2_min)
```

trong đó f_min, f_max lấy từ mặt trận tham chiếu (hợp của tất cả thuật toán).

## Kiểm định thống kê

1. Chạy mỗi thuật toán 30 lần trên mỗi instance (seed ngẫu nhiên khác nhau)
2. Tính HV (hoặc IGD+) cho mỗi lần chạy
3. So sánh các thuật toán theo cặp bằng **kiểm định Wilcoxon rank-sum** (alpha = 0.05)
4. Báo cáo số lần thắng/hòa/thua trên tất cả instance
5. Sử dụng **kiểm định Friedman** để xếp hạng tổng thể trên tất cả instance

## Định dạng báo cáo

### Bảng theo từng instance

| Instance | Chỉ số | Algo1 (mean +/- std) | Algo2 | ... | Tốt nhất |
|----------|--------|----------------------|-------|-----|------|
| C101_A   | HV     | 0.85 +/- 0.02        | 0.82  | ... | Algo1 |
| C101_A   | IGD+   | 0.05 +/- 0.01        | 0.08  | ... | Algo1 |

### Bảng tổng hợp (theo loại instance)

| Loại | Chỉ số | Algo1 | Algo2 | ... |
|----------|--------|-------|-------|-----|
| C1       | HV trung bình | 0.83  | 0.79  | ... |
| R1       | HV trung bình | 0.78  | 0.75  | ... |

### Bảng thắng/hòa/thua

| Algo1 so với | Thắng | Hòa | Thua | (dựa trên Wilcoxon, HV) |
|----------|-----|-----|------|-------------------------|
| NSGA-II  | 95  | 10  | 7    |                         |
| NSGA-III | 88  | 15  | 9    |                         |

## Phân tích hội tụ

Vẽ đồ thị HV theo số lượt đánh giá (tại các mốc 10.000 lượt đánh giá) cho một instance đại diện (ví dụ: R101_A) để thể hiện tốc độ hội tụ.

## Phân tích độ nhạy

Kiểm tra với:
- eps_L trong {10, 25, 50, 100, infinity}: ảnh hưởng của mức độ nghiêm ngặt tardiness
- M trong {3, 5, 7}: ảnh hưởng của kích thước đội xe
- Trên 3 instance đại diện: một từ C1 (cụm/hẹp), một từ R2 (ngẫu nhiên/rộng), một từ RC1 (hỗn hợp/hẹp)

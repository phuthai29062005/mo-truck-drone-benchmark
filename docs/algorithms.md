# Các Thuật toán So sánh

## Tổng quan

Chúng tôi so sánh phương pháp đề xuất với 8 thuật toán thuộc ba nhóm:
metaheuristic đa mục tiêu tổng quát, heuristic chuyên biệt cho bài toán
định tuyến xe tải-drone, và các tiếp cận matheuristic.

## Danh sách thuật toán

### Nhóm 1: Metaheuristic đa mục tiêu tổng quát (baseline)

| # | Thuật toán | Tài liệu tham khảo | Tạp chí/Hội nghị | Năm |
|---|-----------|-----------|-------|------|
| 1 | **NSGA-II** | Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. "A fast and elitist multiobjective genetic algorithm: NSGA-II" | IEEE Trans. Evolutionary Computation, 6(2), 182-197 | 2002 |
| 2 | **NSGA-III** | Deb, K., & Jain, H. "An evolutionary many-objective optimization algorithm using reference-point-based nondominated sorting approach, Part I" | IEEE Trans. Evolutionary Computation, 18(4), 577-601 | 2014 |
| 3 | **MOEA/D** | Zhang, Q., & Li, H. "MOEA/D: A multiobjective evolutionary algorithm based on decomposition" | IEEE Trans. Evolutionary Computation, 11(6), 712-731 | 2007 |

Ba thuật toán này là baseline tiêu chuẩn trong mọi bài báo tối ưu đa mục tiêu.
Chúng cần được điều chỉnh cho bài toán của chúng tôi với các toán tử chuyên biệt (mã hóa, giải mã, sửa chữa).

### Nhóm 2: Heuristic định tuyến xe tải-drone

| # | Thuật toán | Tài liệu tham khảo | Tạp chí/Hội nghị | Năm |
|---|-----------|-----------|-------|------|
| 4 | **GA-SA+NDS** | Ge, H., Chen, S., Chen, G., Chen, W. "Multi-objective optimization for the vehicle-drone routing problem with time windows" | Transportation Research Part E: Logistics and Transportation Review | 2025 |
| 5 | **HGA** | Ha, Q.M., Deville, Y., Pham, Q.D., & Ha, M.H. "A hybrid genetic algorithm for the traveling salesman problem with drone" | Journal of Heuristics, 26, 219-247 | 2020 |
| 6 | **ALNS** | Sacramento, D., Pisinger, D., & Ropke, S. "An adaptive large neighborhood search metaheuristic for the vehicle routing problem with drones" | Transportation Research Part C: Emerging Technologies, 102, 289-315 | 2019 |
| 7 | **HVNS+DP** | Ren, K., Yin, Y., Wang, S., & Chen, Z. "A branch-and-price algorithm for the vehicle routing problem with drones and multiple visits" | European Journal of Operational Research | 2024 |

Ghi chú:
- **GA-SA+NDS**: Lai GA + simulated annealing với sắp xếp không bị trội. Cùng lớp bài toán (xe tải-drone đa mục tiêu với TW).
- **HGA**: Thuật toán di truyền lai cho TSP-D. Cần mở rộng để xử lý TW, sạc từng phần, và đa mục tiêu.
- **ALNS**: Tìm kiếm lân cận lớn thích nghi cho VRP-D. Cần mở rộng với wrapper đa mục tiêu.
- **HVNS+DP**: VNS lai với DP pricing. Đơn mục tiêu nhưng có cấu trúc liên quan.

### Nhóm 3: Tiếp cận đa mục tiêu từ bài toán liên quan

| # | Thuật toán | Tài liệu tham khảo | Tạp chí/Hội nghị | Năm |
|---|-----------|-----------|-------|------|
| 8 | **BOA-KS** | Multi-objective butterfly optimization with knapsack-based selection | Expert Systems with Applications (ESWA) | 2024 |

## Hướng dẫn cài đặt khi điều chỉnh thuật toán

### Chuyển đổi thuật toán đơn mục tiêu sang đa mục tiêu

Với các thuật toán 5, 6, 7 (ban đầu là đơn mục tiêu):
- Bọc bằng **epsilon-constraint**: cố định makespan <= T_bar, tối thiểu hóa energy. Quét T_bar trên một lưới giá trị.
- Hoặc bọc bằng **weighted-sum scalarization**: min lambda * T_max + (1-lambda) * E_system. Quét lambda trong [0, 1].
- Thu thập tất cả lời giải qua các lần quét, lọc lấy các lời giải không bị trội.

### Điều chỉnh cho đặc thù bài toán

Tất cả thuật toán cần các điều chỉnh sau:
1. **Phân công drone**: quyết định khách hàng nào được drone phục vụ và khách hàng nào xe tải phục vụ
2. **Điểm linh hoạt**: cho phép chèn các điểm linh hoạt làm điểm phóng/thu hồi
3. **Sạc từng phần**: lập lịch sạc tại điểm dừng và trong segment xe tải thuần
4. **Khả thi pin**: kiểm tra B_{k,h} >= E^D + B_min trước mỗi chuyến bay
5. **Đồng bộ hóa**: tính thời gian bay lơ lửng/chờ đợi tại nút thu hồi
6. **Cửa sổ thời gian mềm**: tính tardiness, đảm bảo L_total <= eps_L
7. **Bắt buộc drone (biến thể B)**: đảm bảo khách hàng forced_drone KHÔNG nằm trong tuyến xe tải

### Đề xuất mã hóa (cho các phương pháp dựa trên GA)

Nhiễm sắc thể hai lớp:
- **Lớp 1 (hoán vị pi)**: thứ tự thăm tất cả khách hàng (giant tour)
- **Lớp 2 (nhị phân b)**: với mỗi khách hàng drone-eligible, 0 = xe tải, 1 = drone
- **Giải mã**: chia giant tour thành tuyến xe tải; phân công khách hàng drone vào chuyến bay; lập lịch sạc; tính mục tiêu

### Thư viện toán tử

Toán tử phá hủy: loại bỏ ngẫu nhiên, loại bỏ tệ nhất (theo đóng góp tardiness), loại bỏ tuyến, loại bỏ liên quan drone, loại bỏ theo cửa sổ thời gian.

Toán tử sửa chữa: chèn tham lam (theo min tăng mục tiêu), chèn regret-k, chèn ưu tiên drone.

Tìm kiếm cục bộ: 2-opt, or-opt, swap (trong/giữa tuyến), chuyển đổi drone (xe tải ↔ drone), chèn/loại bỏ điểm linh hoạt.

## Thiết lập thí nghiệm

| Tham số | Giá trị |
|-----------|-------|
| Số lần chạy mỗi instance | 30 (seed ngẫu nhiên khác nhau) |
| Số lượt đánh giá tối đa | 500.000 mỗi lần chạy |
| Giới hạn thời gian | 600 giây mỗi lần chạy (instance 100 khách hàng) |
| Kích thước quần thể (phương pháp GA) | 100 |
| Số cặp M | 5 |
| Giới hạn tardiness eps_L | 50.0 |
| Kiểm định thống kê | Wilcoxon rank-sum, mức ý nghĩa 0.05 |

## Cách nộp kết quả

1. Chạy thuật toán của bạn 30 lần trên mỗi instance trong tổng số 112 instance
2. Lưu kết quả theo định dạng trong `output_format.md`
3. Sử dụng script đánh giá để tính các chỉ số

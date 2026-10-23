# Bộ Benchmark cho Bài toán Định tuyến Xe tải-Drone Đa mục tiêu

**Định tuyến xe tải-drone đa mục tiêu với điểm hẹn linh hoạt, sạc từng phần và cửa sổ thời gian mềm**

## Tổng quan bài toán

- **M** cặp xe tải-drone; mỗi xe tải mang chính xác một drone
- Mỗi chuyến bay drone phục vụ đúng 1 khách hàng; phóng tại điểm dừng h, thu hồi tại điểm dừng h+1
- Điểm thu hồi: kho hàng (depot), khách hàng, hoặc điểm linh hoạt (flexible site)
- Sạc từng phần: trên xe tải đang di chuyển (tốc độ rho_m) hoặc khi xe dừng (tốc độ rho_s, tốn thêm thời gian dừng)
- Cửa sổ thời gian mềm: tổng trễ có trọng số là ràng buộc (L_total <= eps_L), không phải mục tiêu
- **Mục tiêu**: tối thiểu hóa makespan T_max VÀ tối thiểu hóa tổng năng lượng hệ thống E_system
- **Đầu ra**: xấp xỉ mặt trận Pareto

## Cấu trúc thư mục

```
mo-truck-drone-benchmark/
  README.md                    # File này
  docs/
    problem_specification.md   # Mô hình toán học đầy đủ
    input_format.md            # Định dạng đầu vào JSON
    output_format.md           # Định dạng đầu ra cho mặt trận Pareto
    algorithms.md              # Các thuật toán so sánh kèm tài liệu tham khảo
    evaluation.md              # Chỉ số đánh giá và quy trình thực nghiệm
  instances/                   # 112 bộ test (56 cơ sở x 2 biến thể)
    C101_A.json ... RC208_B.json
  scripts/
    evaluate.py                # Tính HV, IGD+, epsilon indicator
    validate_solution.py       # Kiểm tra tính khả thi của lời giải
    generate_instances.py      # Sinh bộ test (để tái tạo)
```

## Bộ test

56 instance kiểu Solomon với 100 khách hàng, chia thành 6 loại, mỗi loại có 2 biến thể:

| Loại | Số lượng | Phân bố không gian | Cửa sổ thời gian |
|------|----------|--------------------|--------------------|
| C1 (C101-C109) | 9 | Cụm (Clustered) | Hẹp (Tight) |
| C2 (C201-C208) | 8 | Cụm (Clustered) | Rộng (Wide) |
| R1 (R101-R112) | 12 | Ngẫu nhiên (Random) | Hẹp (Tight) |
| R2 (R201-R211) | 11 | Ngẫu nhiên (Random) | Rộng (Wide) |
| RC1 (RC101-RC108) | 8 | Hỗn hợp (Mixed) | Hẹp (Tight) |
| RC2 (RC201-RC208) | 8 | Hỗn hợp (Mixed) | Rộng (Wide) |

**Biến thể A** (lợi thế tự nhiên của UAV): tất cả cạnh tồn tại; xe tải sử dụng hệ số đường vòng 1.3 lần khoảng cách Euclidean, drone bay theo đường Euclidean với tốc độ cao hơn (40 so với 30).

**Biến thể B** (bắt buộc dùng UAV): ~15% khách hàng không thể tiếp cận bằng xe tải (chỉ drone phục vụ được). Đây là các khách hàng drone-eligible gần depot nhất.

## Hướng dẫn nhanh

1. Chọn một instance, ví dụ: `instances/R101_A.json`
2. Chạy thuật toán của bạn; xuất kết quả theo định dạng trong `docs/output_format.md`
3. Kiểm tra tính khả thi: `python scripts/validate_solution.py R101_A.json your_solution.json`
4. Đánh giá: `python scripts/evaluate.py --ref reference_front.json your_solution.json`

## Thuật toán so sánh

Xem `docs/algorithms.md` để biết danh sách đầy đủ kèm tài liệu tham khảo.

## Chỉ số đánh giá

Xem `docs/evaluation.md` để biết quy trình: HV, IGD+, epsilon indicator, #ND, runtime.

## Trích dẫn

Nếu bạn sử dụng bộ benchmark này, vui lòng trích dẫn:
```
[Tham khảo bài báo - sẽ cập nhật]
```

## Giấy phép

Bộ benchmark và các script đánh giá được phát hành cho mục đích nghiên cứu học thuật.

# Định dạng Đầu ra

Mỗi thuật toán phải xuất một file JSON chứa xấp xỉ mặt trận Pareto.

## Schema file lời giải

```json
{
  "instance": "R101_A",                // Tên instance + biến thể
  "algorithm": "NSGA-II",             // Tên thuật toán
  "n_pairs": 5,                       // Số cặp xe tải-drone sử dụng
  "eps_L": 50.0,                      // Giới hạn tardiness sử dụng
  "runtime_seconds": 123.4,           // Thời gian chạy thực tế (wall-clock)
  "n_evaluations": 500000,            // Tổng số lượt đánh giá lời giải
  "seed": 42,                         // Hạt giống ngẫu nhiên
  "run_id": 1,                        // Số thứ tự lần chạy (cho thí nghiệm nhiều lần)

  "pareto_front": [                   // Danh sách các lời giải không bị trội
    {
      "id": 1,
      "makespan": 185.3,              // f_1: T_max
      "energy": 1234.5,               // f_2: E_system
      "tardiness": 12.0,              // L_total (phải <= eps_L)
      "n_drone_sorties": 15,          // Số chuyến bay drone sử dụng
      "routes": [                      // Tùy chọn: chi tiết tuyến đường
        {
          "pair_id": 1,               // Cặp xe tải-drone k
          "truck_route": [0, 3, 12, 45, 0],  // Thứ tự điểm dừng xe tải (ID nút)
          "segments": [
            {
              "type": "truck",        // Segment xe tải thuần
              "from": 0,
              "to": 3,
              "depart_time": 0.0,
              "arrive_time": 5.2,
              "charge_time": 0.0,     // c_{k,h}: thời gian dừng thêm để sạc
              "charge_amount": 0.0    // q_{k,h}: lượng pin được sạc
            },
            {
              "type": "drone",        // Segment hợp tác (chuyến bay drone)
              "from": 3,              // Nút phóng
              "to": 12,              // Nút thu hồi
              "drone_customer": 7,    // Khách hàng được drone phục vụ
              "depart_time": 14.2,
              "arrive_time": 22.8,
              "drone_energy": 0.15,   // E^D cho chuyến bay này
              "hover_time": 1.3,      // H^D: thời gian drone bay lơ lửng chờ
              "truck_wait": 0.0,      // W^T: thời gian xe tải chờ drone
              "charge_time": 2.0,
              "charge_amount": 0.1,
              "battery_before": 0.85, // B_{k,h} trước khi sạc
              "battery_after": 0.80   // B_{k,h+1} sau chuyến bay
            }
            // ... thêm các segment
          ]
        }
        // ... thêm các cặp
      ]
    }
    // ... thêm các lời giải không bị trội
  ]
}
```

## Đầu ra tối thiểu (chỉ các trường bắt buộc)

Tối thiểu, cần cung cấp các điểm trên mặt trận Pareto với giá trị mục tiêu và tính khả thi:

```json
{
  "instance": "R101_A",
  "algorithm": "NSGA-II",
  "runtime_seconds": 123.4,
  "seed": 42,
  "run_id": 1,
  "pareto_front": [
    {"makespan": 185.3, "energy": 1234.5, "tardiness": 12.0},
    {"makespan": 192.1, "energy": 1100.2, "tardiness": 8.5},
    {"makespan": 210.0, "energy": 980.0,  "tardiness": 0.0}
  ]
}
```

## Lưu ý

1. **Tất cả lời giải trong `pareto_front` phải khả thi**: `tardiness <= eps_L`, ràng buộc pin thỏa mãn, mọi khách hàng được phục vụ đúng một lần, v.v.
2. **Không bị trội**: mặt trận chỉ chứa các lời giải không bị trội lẫn nhau (trong không gian (makespan, energy)).
3. **Nhiều lần chạy**: chạy mỗi thuật toán 30 lần với các seed khác nhau. Mỗi lần chạy tạo một file. Đặt tên file theo: `{algorithm}_{instance}_{run_id}.json`.
4. **Chi tiết tuyến đường là tùy chọn** nhưng được khuyến nghị để kiểm tra tính khả thi. Script kiểm tra có thể xác minh tính khả thi khi có thông tin tuyến đường.
5. Các điểm linh hoạt trong `truck_route` sử dụng ID dạng chuỗi (ví dụ: "F3").

## Quy ước đặt tên file

```
results/
  {algorithm}/
    {algorithm}_{instance}_{run_id}.json
```

Ví dụ:
```
results/
  NSGA-II/
    NSGA-II_R101_A_01.json
    NSGA-II_R101_A_02.json
    ...
    NSGA-II_R101_A_30.json
    NSGA-II_R101_B_01.json
    ...
```

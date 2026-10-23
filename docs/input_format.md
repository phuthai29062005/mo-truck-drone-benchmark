# Định dạng Đầu vào

Mỗi instance là một file JSON. Dưới đây là schema kèm mô tả các trường.

## Schema JSON

```json
{
  "name": "C101",                    // Tên instance (kiểu Solomon)
  "n_customers": 100,               // Số lượng khách hàng
  "variant": "A_natural" | "B_forced",  // Loại biến thể
  "depot": {
    "x": 50.0,                       // Tọa độ x của depot
    "y": 50.0                        // Tọa độ y của depot
  },
  "truck_capacity": 200,            // Q^T: tải trọng tối đa xe tải
  "horizon": 230,                   // Horizon lập kế hoạch (due date của depot)

  "customers": [                     // Mảng n_customers đối tượng
    {
      "id": 1,                       // ID khách hàng (đánh số từ 1)
      "x": 12.6,                     // Tọa độ x
      "y": 45.7,                     // Tọa độ y
      "demand": 22,                  // d_i: nhu cầu (khối lượng)
      "ready_time": 145,            // e_i: thời điểm phục vụ sớm nhất
      "due_time": 173,              // l_i: thời điểm phục vụ muộn nhất mong muốn
      "service_time": 9,            // s_i (dùng cho cả s_i^T và s_i^D)
      "drone_eligible": false,      // true nếu khách hàng thuộc C^D
      "truck_only": true,           // true nếu khách hàng BẮT BUỘC phục vụ bằng xe tải
      "forced_drone": false         // true nếu cạnh xe tải bị loại (chỉ biến thể B)
    }
    // ... (100 khách hàng)
  ],

  "flexible_sites": [               // Các điểm phóng/thu hồi linh hoạt F
    {
      "id": "F1",                    // ID điểm
      "x": 35.2,                     // Tọa độ x
      "y": 67.8                      // Tọa độ y
    }
    // ... (~10 điểm)
  ],

  "drone_params": {                  // Tham số drone và sạc
    "drone_speed": 40.0,            // v_drone (đơn vị khoảng cách / đơn vị thời gian)
    "truck_speed": 30.0,            // v_truck
    "battery_max": 1.0,             // B_max (chuẩn hóa)
    "battery_min": 0.1,             // B_min (dự trữ an toàn)
    "charge_rate_stopped": 0.05,    // ρ_s (pin / đơn vị thời gian)
    "charge_rate_moving": 0.02,     // ρ_m (pin / đơn vị thời gian)
    "launch_time": 1.0,             // ℓ (đơn vị thời gian)
    "recovery_time": 1.0,           // r (đơn vị thời gian)
    "drone_payload_cap": 10,        // Q^D
    "P0": 0.005,                    // Công suất cơ sở drone (không tải)
    "alpha": 0.001,                 // Mức tăng công suất trên mỗi đơn vị tải trọng
    "hover_power": 0.008,           // P_hover
    "detour_factor": 1.3,           // Khoảng cách xe tải = detour_factor × Euclidean
    "forced_drone_pct": 0.15        // Tỉ lệ khách hàng bắt buộc drone (biến thể B)
  },

  "drone_eligible_set": [4, 7, ...],   // Danh sách ID khách hàng drone-eligible
  "forced_drone_only": [4, 7, ...]     // Danh sách ID khách hàng chỉ drone (biến thể B)
}
```

## Tính khoảng cách và thời gian

```python
import math

def euclidean(a, b):
    return math.sqrt((a["x"] - b["x"])**2 + (a["y"] - b["y"])**2)

# Thời gian di chuyển xe tải giữa nút i và g:
def truck_time(node_i, node_g, params):
    dist = params["detour_factor"] * euclidean(node_i, node_g)
    return dist / params["truck_speed"]

# Thời gian bay drone giữa nút i và j:
def drone_time(node_i, node_j, params):
    dist = euclidean(node_i, node_j)
    return dist / params["drone_speed"]

# Năng lượng chuyến bay drone (phóng tại i, phục vụ j, thu hồi tại g):
def drone_energy(node_i, node_j, node_g, demand_j, hover_time, params):
    dist_ij = euclidean(node_i, node_j)
    dist_jg = euclidean(node_j, node_g)
    t_ij = dist_ij / params["drone_speed"]
    t_jg = dist_jg / params["drone_speed"]
    energy = (params["P0"] + params["alpha"] * demand_j) * t_ij  # có tải
    energy += params["P0"] * t_jg                                 # không tải
    energy += params["hover_power"] * hover_time                  # lơ lửng
    return energy

# Năng lượng xe tải (đơn giản hóa: tỉ lệ với khoảng cách):
def truck_energy(node_i, node_g, params):
    return params["detour_factor"] * euclidean(node_i, node_g)
```

## Tham số bổ sung (không có trong file instance)

Đây là các tham số mức thí nghiệm do người chạy thuật toán thiết lập:

| Tham số | Ký hiệu | Mặc định | Mô tả |
|---------|----------|----------|-------|
| Số cặp | M | 5 | Số cặp xe tải-drone |
| Giới hạn tardiness | eps_L | 50.0 | Tổng tardiness có trọng số tối đa |
| Trọng số tardiness | w_i | 1.0 | Trọng số mỗi khách hàng (đồng nhất) |
| Hiệu suất sạc | η_c | 1.0 | Hệ số hiệu suất sạc |
| Pin ban đầu | B_k^0 | 1.0 | = B_max |

## Biến thể B: khách hàng bắt buộc drone

Trong các instance biến thể B, khách hàng có `forced_drone: true` **không có cạnh xe tải**. Xe tải không thể ghé thăm các khách hàng này. Họ phải được:
1. Phân công vào chuyến bay drone, VÀ
2. Drone phải được phóng từ và thu hồi tại các nút xe tải có thể tiếp cận.

Nếu thuật toán của bạn biểu diễn tuyến xe tải dạng hoán vị, khách hàng forced-drone KHÔNG ĐƯỢC xuất hiện trong tuyến xe tải. Họ chỉ xuất hiện dưới dạng phân công drone j_{k,h}.

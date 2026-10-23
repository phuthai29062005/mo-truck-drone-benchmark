# Đặc tả Bài toán

## Định tuyến xe tải-drone đa mục tiêu với điểm hẹn linh hoạt, sạc từng phần và cửa sổ thời gian mềm

### 1. Loại bài toán

Tĩnh, ngoại tuyến, tất định. Mọi dữ liệu đã biết trước khi lập kế hoạch.

### 2. Cấu hình hệ thống

1. **M** cặp xe tải-drone. Mỗi xe tải mang chính xác một drone.
2. Xe tải xuất phát từ và quay về kho hàng (depot, nút 0).
3. Mỗi khách hàng được phục vụ đúng một lần, bởi xe tải hoặc drone.
4. Mỗi chuyến bay drone phục vụ đúng **một** khách hàng.
5. Drone phóng tại điểm dừng h của xe tải và thu hồi tại điểm dừng h+1.
6. Nút phóng/thu hồi có thể là: depot, nút khách hàng, hoặc điểm linh hoạt (flexible site).
7. Drone phải quay về **cùng** xe tải đã phóng nó.
8. Các chuyến bay của cùng một cặp không chồng chéo.
9. Xe tải và drone đồng bộ tại nút thu hồi trước khi tiếp tục.
10. Drone được sạc (từng phần) khi ở trên xe tải: khi xe di chuyển hoặc khi xe dừng.
11. Drone KHÔNG được sạc trong khi đang bay (sortie).
12. Khách hàng có cửa sổ thời gian mềm [e_i, l_i]. Đến sớm thì chờ; đến trễ bị tính tardiness.

### 3. Các tập hợp

- **C** = {1, ..., n}: tập khách hàng
- **F** = {n+1, ..., n+f}: tập điểm linh hoạt phóng/thu hồi
- **V** = {0} ∪ C ∪ F: tất cả các nút; 0 = depot
- **K** = {1, ..., M}: tập cặp xe tải-drone
- **C^D** = {i ∈ C : d_i ≤ Q^D và i đủ điều kiện bay drone}: tập khách hàng drone-eligible

### 4. Tham số

#### 4.1 Tham số khách hàng
Với mỗi khách hàng i ∈ C:
- **d_i**: nhu cầu (khối lượng/thể tích)
- **s_i^T**: thời gian phục vụ bằng xe tải tại khách hàng i
- **s_i^D**: thời gian phục vụ bằng drone tại khách hàng i
- **e_i**: thời điểm phục vụ sớm nhất (ready time)
- **l_i**: thời điểm phục vụ muộn nhất mong muốn (due date)
- **w_i** ≥ 0: trọng số tardiness

Với depot và điểm linh hoạt: s_i^T = s_i^D = 0.

#### 4.2 Tham số phương tiện
- **Q^T**: sức chứa xe tải
- **Q^D**: tải trọng drone (= drone_payload_cap)
- **B_max**: dung lượng pin tối đa (chuẩn hóa về 1.0)
- **B_min**: mức pin an toàn tối thiểu (= 0.1)
- **B_k^0**: pin ban đầu của drone k (= B_max)
- **rho_s**: tốc độ sạc khi xe dừng (= 0.05 mỗi đơn vị thời gian)
- **rho_m**: tốc độ sạc khi xe di chuyển, drone trên xe (= 0.02 mỗi đơn vị thời gian)
- **eta_c**: hiệu suất sạc (= 1.0 trong benchmark)
- **ℓ** (ell): thời gian chuẩn bị phóng (= 1.0)
- **r**: thời gian thu hồi (= 1.0)

#### 4.3 Thời gian di chuyển và năng lượng
- **v_truck** = 30: tốc độ xe tải
- **v_drone** = 40: tốc độ drone
- **τ^T_{ig}** = dist_truck(i,g) / v_truck: thời gian di chuyển xe tải
  - Biến thể A: dist_truck(i,g) = detour_factor × euclidean(i,g) = 1.3 × euclidean(i,g)
  - Biến thể B: dist_truck(i,g) = 1.3 × euclidean(i,g), nhưng một số cạnh bị loại bỏ (khách hàng forced_drone)
- **τ^D_{ij}** = euclidean(i,j) / v_drone: thời gian bay drone
- **E^T_{ig}**: năng lượng xe tải = tỉ lệ với dist_truck(i,g) (đơn giản hóa: E^T = dist_truck)
- **P_0** = 0.005: công suất cơ sở drone (không tải)
- **α** = 0.001: mức tăng công suất trên mỗi đơn vị tải trọng
- **P_hover** = 0.008: công suất bay lơ lửng
- **E_{L/R}**: năng lượng phóng/thu hồi (đơn giản hóa: 0 trong benchmark, đã tính trong thời gian sortie)

#### 4.4 Mô hình năng lượng drone

Cho một segment hợp tác (phóng tại i, phục vụ khách hàng j, thu hồi tại g):

```
E^D_{ijg} = (P_0 + α × d_j) × τ^D_{ij}    # bay có tải i → j
           + P_0 × τ^D_{jg}                  # bay không tải j → g
           + P_hover × H^D                    # chờ lơ lửng
           + E_{L/R}                           # năng lượng phóng/thu hồi
```

#### 4.5 Chất lượng dịch vụ
- **eps_L**: tổng tardiness có trọng số tối đa cho phép

### 5. Biểu diễn lời giải

Một lời giải X bao gồm, cho mỗi cặp k:
- Tuyến xe tải: R_k = (v_{k,0}, v_{k,1}, ..., v_{k,H_k}), với v_{k,0} = v_{k,H_k} = 0
- Loại segment: u_{k,h} ∈ {0, 1}. 0 = xe tải thuần, 1 = hợp tác (chuyến bay drone)
- Phân công drone: j_{k,h} cho các segment hợp tác
- Kế hoạch sạc: q_{k,h} (lượng sạc), c_{k,h} (thời gian dừng để sạc)

### 6. Tính thời gian

#### 6.1 Xe tải tại điểm dừng
```
D_{k,h} = max(A_{k,h}, e_{v_{k,h}}) + σ_{k,h} + c_{k,h}
```
trong đó σ_{k,h} = s^T_{v_{k,h}} nếu xe tải phục vụ khách hàng tại đó, 0 nếu ngược lại.

#### 6.2 Segment xe tải thuần (u_{k,h} = 0)
```
A_{k,h+1} = D_{k,h} + τ^T_{v_{k,h}, v_{k,h+1}}
```

#### 6.3 Segment hợp tác (u_{k,h} = 1)
Nút phóng i = v_{k,h}, khách hàng drone j = j_{k,h}, nút thu hồi g = v_{k,h+1}.

```
A_j^D = D_{k,h} + ℓ + τ^D_{ij}              # drone đến khách hàng
S_j^D = max(A_j^D, e_j)                      # drone bắt đầu phục vụ
C_j   = S_j^D + s_j^D                        # hoàn thành phục vụ

Δ^D = ℓ + τ^D_{ij} + max(0, e_j - A_j^D) + s_j^D + τ^D_{jg}
Δ^T = τ^T_{ig}

W^T  = max(0, Δ^D - Δ^T)                     # xe tải chờ drone
H^D  = max(0, Δ^T - Δ^D)                     # drone bay lơ lửng chờ xe tải

A_{k,h+1} = D_{k,h} + max(Δ^T, Δ^D) + r
```

### 7. Động lực học pin

```
B_{k,0}   = B_k^0                            # pin ban đầu

# Lượng sạc giới hạn bởi:
0 ≤ q_{k,h} ≤ η_c × [ρ_s × c_{k,h} + (1 - u_{k,h}) × ρ_m × τ^T]

# Không vượt quá max:
B_{k,h} + q_{k,h} ≤ B_max

# Phải đủ pin trước khi phóng:
B_{k,h} + q_{k,h} ≥ E^D + B_min   (nếu u_{k,h} = 1)

# Cập nhật:
B_{k,h+1} = B_{k,h} + q_{k,h} - u_{k,h} × E^D

# Giới hạn:
B_min ≤ B_{k,h} ≤ B_max   với mọi k, h
```

### 8. Cửa sổ thời gian mềm

```
L_i = max(0, C_i - l_i)                      # độ trễ
L_total = Σ_{i ∈ C} w_i × L_i               # tổng tardiness có trọng số
L_total ≤ eps_L                              # ràng buộc
```

### 9. Mục tiêu

```
f_1(X) = T_max = max_{k ∈ K} A_{k, H_k}    # tối thiểu hóa makespan
f_2(X) = E_truck + E_drone / η_c            # tối thiểu hóa tổng năng lượng hệ thống

min (f_1, f_2)   thỏa mãn tất cả ràng buộc trên
```

Đầu ra: xấp xỉ mặt trận Pareto (tập các lời giải không bị trội).

### 10. Chi tiết Biến thể B

Trong biến thể B, các khách hàng được đánh dấu `forced_drone: true` không có cạnh xe tải. Họ BẮT BUỘC phải được phục vụ bằng drone. Xe tải không thể ghé thăm họ. Thuật toán phải đảm bảo các khách hàng này được phân công vào chuyến bay drone.

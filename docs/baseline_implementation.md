# Triển khai NSGA-II, NSGA-III và MOEA/D

## Phạm vi

Ba baseline chạy bằng Python >= 3.9, chỉ dùng standard library. Các thuật toán
dùng chung biểu diễn nghiệm, khởi tạo, toán tử và bộ mô phỏng để so sánh công bằng.
Chưa thực hiện thí nghiệm 30 lần × 112 instance; chưa có kết luận về chất lượng
hay thứ hạng các thuật toán trên dữ liệu thật.

## Vấn đề trong benchmark hiện tại

**112/112 instance không thể khả thi với M=5, Qᵀ=200.** Tổng nhu cầu mỗi instance
vượt 1.000. Xe tải mang cả hàng giao bằng drone nên việc chuyển phương thức phục vụ
không khắc phục được thiếu tải. Ví dụ R101 có tổng nhu cầu 2.083, cần ít nhất
11 cặp nếu sức chứa vẫn là 200. Đây chỉ là cận dưới cần thiết, không bảo đảm khả thi
về cửa sổ thời gian hay phân chia hàng hóa.

Theo quyết định hiện tại, giữ nguyên đặc tả và dữ liệu, chờ nhóm chốt cấu hình.
Precheck trả `status=infeasible_precheck`, `n_evaluations=0`, mặt trận rỗng và
nguyên nhân. Mặt trận rỗng không phải kết quả tối ưu thành công.

Các file A và B cùng tên chỉ khác trường `variant`; A vẫn chứa cờ và danh sách
forced-drone của B do script sinh dữ liệu. Theo mô tả biến thể trong đặc tả,
bộ giải và validator chỉ áp dụng các cờ này khi `variant` bắt đầu bằng `B`.
Không sửa trực tiếp các file instance.

## Cấu trúc mã

- `truck_drone/model.py`: khoảng cách, thời gian, năng lượng, tải hàng, pin,
  đồng bộ và weighted completion tardiness; kiểm tra điều kiện cần trước khi chạy.
- `truck_drone/encoding.py`: mã hóa, khởi tạo, lai ghép, đột biến, sửa phân công,
  giải mã tuyến và lập lịch sạc.
- `truck_drone/algorithms.py`: ba vòng lặp tiến hóa và archive khả thi dùng chung.
- `truck_drone/__main__.py`: CLI chạy đơn/batch và xuất JSON đầy đủ tuyến.
- `scripts/validate_solution.py`: phát lại tuyến, kiểm tra vật lý và đối chiếu
  mục tiêu, thời gian, pin được khai báo.

## Mã hóa và giải mã dùng chung

Nhiễm sắc thể gồm hoán vị tất cả khách hàng và các gene theo ID khách hàng:
phương thức phục vụ, cặp phụ trách, điểm linh hoạt tùy chọn và mức sạc dự phòng.
ID không bắt buộc liên tiếp.

Khởi tạo kết hợp thứ tự ready time, ready time có nhiễu và hoán vị ngẫu nhiên.
Phân công ban đầu ưu tiên tải khả thi, thời gian hoàn thành và hạn phục vụ.
Lai ghép dùng order crossover cho hoán vị và uniform crossover cho gene còn lại.
Đột biến gồm swap, đảo đoạn, relocate, đổi cặp, đổi phương thức, điểm hẹn và mức sạc.
Các xác suất được ghi trực tiếp trong `Encoding.offspring`, không thay đổi theo
thuật toán.

Giải mã sửa gene phương thức: forced-drone luôn bay; khách hàng không đủ điều kiện
luôn đi xe tải. Nếu cặp chỉ định quá tải, chuyển sang cặp còn chỗ, ưu tiên tải thấp.
Sửa chữa này là heuristic, có thể còn vi phạm dù instance có nghiệm.

Drone phóng ở điểm dừng hiện tại và thu hồi ở điểm dừng kế tiếp. Nếu khách kế tiếp
được xe tải phục vụ thì dùng khách đó làm điểm thu hồi; gene điểm linh hoạt có thể
chọn thu hồi tại site trước khi tiếp tục đến khách. Các khách drone liên tiếp dùng
site gần hoặc depot nếu không có site. Không lặp khách xe tải làm điểm trung gian
vì mỗi lần ghé khách được tính là một lần phục vụ. Mỗi cặp chỉ có một tuyến,
không tái nạp hàng ở depot giữa tuyến.

Sạc di động chỉ diễn ra trong segment thuần xe tải, giới hạn bởi dung lượng pin.
Sạc dừng dùng thời gian dừng thêm, chỉ bổ sung lượng cần cho chuyến bay và dự phòng
theo gene. Dùng bisection để tính đồng thời thời gian sạc và năng lượng hover vì
thời điểm phóng ảnh hưởng thời gian chờ tại khách. Không cộng sạc trong thời gian
phục vụ, chờ cửa sổ thời gian hay khi drone bay. Nếu năng lượng chuyến bay vượt
dung lượng khả dụng thì giữ vi phạm để chọn lọc, không báo nghiệm khả thi.

Không có tìm kiếm cục bộ riêng hay heuristic bí mật cho từng thuật toán.

## Ba cơ chế tiến hóa

- **NSGA-II**: constrained non-dominated sorting, binary tournament theo rank
  và crowding distance, gộp cha–con và chọn elitist bằng crowding ở front cuối.
- **NSGA-III**: constrained non-dominated sorting, tournament theo rank và hòa
  ngẫu nhiên, chọn front cuối bằng reference-point niching. Với hai mục tiêu,
  tạo N hướng đều trên simplex `(i/(N−1), 1−i/(N−1))`. Chuẩn hóa bằng ideal point,
  ASF extreme points và hyperplane intercepts hai chiều; nếu suy biến dùng cực đại
  từng thành phần. Liên kết theo khoảng cách vuông góc; ưu tiên niche ít đại diện,
  chọn điểm gần hướng nhất khi niche trống, ngẫu nhiên khi niche đã có điểm.
- **MOEA/D**: N trọng số đều, lân cận tối đa 20 trọng số gần nhất, chọn hai cha
  trong lân cận, cập nhật ideal point và thay nghiệm lân cận bằng scalarization
  Tchebycheff. Trọng số 0 được thay bằng 1e-6. Dùng đơn vị mục tiêu gốc, không
  chuẩn hóa Tchebycheff. Phiên bản này dùng các toán tử hoán vị chung thay cho
  toán tử biến thực, và thêm feasibility-first để xử lý ràng buộc bài toán.

Vi phạm tổng hợp là tổng vượt tải / Qᵀ, thiếu/thừa pin / Bmax, vượt tardiness /
max(1, eps_L), cộng vi phạm cấu trúc. Feasible luôn thắng infeasible; hai nghiệm
infeasible ưu tiên vi phạm nhỏ hơn; khi bằng nhau dùng mục tiêu/cơ chế chọn tương ứng.
Archive ngoài lưu **mọi nghiệm khả thi không bị trội đã đánh giá**, loại điểm mục tiêu
trùng nhau. Không xuất nghiệm infeasible vào `pareto_front`.

Các tài liệu gốc tham chiếu:

- Deb et al. (2002), [NSGA-II](https://doi.org/10.1109/4235.996017).
- Deb & Jain (2014), [NSGA-III, bản thảo của tác giả](https://www.egr.msu.edu/~kdeb/papers/k2012009.pdf).
- Zhang & Li (2007), [MOEA/D](https://doi.org/10.1109/TEVC.2007.892759).

## Chạy chương trình

Từ thư mục gốc repo:

```bash
# Cấu hình đúng đặc tả; hiện sẽ báo infeasible_precheck vì thiếu tổng tải.
python3 -m truck_drone instances/R101_A.json --algorithm all

# Một thuật toán, giới hạn ngân sách nhỏ để kiểm tra tích hợp.
python3 -m truck_drone instances/R101_B.json --algorithm NSGA-III \
  --population 20 --evaluations 200 --time-limit 10 --output-dir results/smoke

# Cú pháp batch đầy đủ, chỉ dùng sau khi nhóm chốt cấu hình khả thi.
python3 -m truck_drone instances --algorithm all --runs 30 --seed 42 \
  --population 100 --evaluations 500000 --time-limit 600
```

Mỗi lần chạy dùng seed `seed + run_id − 1`. Ba thuật toán nhận cùng seed và ngân
sách. Điều kiện dừng là điều kiện đạt trước giữa số lượt đánh giá và wall-clock.
Kiểm tra thời gian trước mỗi lần giải mã; có thể vượt nhẹ giới hạn do một lần
giải mã hoặc chọn lọc đang thực hiện. Tái lập chính xác khi ngân sách đánh giá
kết thúc trước thời gian; chạy dừng theo wall-clock có thể khác giữa máy.

Tham số `--M`, `--eps-L`, `--truck-capacity`, `--eta-c` hỗ trợ cấu hình thí nghiệm
được nhóm quyết định sau này. Mọi giá trị được ghi vào file kết quả. Mặc định
không đổi sức chứa trong instance. Không tự động tăng M hay sức chứa.

File xuất theo `results/{algorithm}/{algorithm}_{instance}_{run_id}.json`.
`MOEA/D` được thay `/` bằng `_` trong đường dẫn để không tạo thư mục lồng nhầm.
Không ghi đè file kết quả cũ: chọn `--output-dir` khác để chạy lại.

Trạng thái `ok` nghĩa là tìm được ít nhất một nghiệm khả thi.
`no_feasible_solution` nghĩa là chưa tìm được nghiệm trong ngân sách, **không**
chứng minh bài toán bất khả thi. Chẩn đoán ghi mức vi phạm tốt nhất đã tìm được.
CLI trả mã 2 nếu bất kỳ lần chạy nào không thành công, mã 0 khi tất cả thành công.

## Xác minh

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_solution.py instances/R101_A.json \
  results/NSGA-II/NSGA-II_R101_A_01.json
```

Validator đọc M, eps_L, sức chứa và hiệu suất sạc từ metadata kết quả; `--M`
và `--eps_L` có thể ghi đè. Khác validator cũ, mục tiêu không có tuyến không đủ
để chứng nhận khả thi. Từng segment phải khớp hai điểm dừng liên tiếp; kiểm tra
phục vụ đúng một lần, tải drone/xe, cờ forced-drone, tốc độ sạc, giới hạn pin,
thời gian đồng bộ, completion tardiness và mục tiêu tính lại.

Tests bao gồm kết quả tính tay, sạc từng phần, hiệu suất sạc, thời gian chờ sớm,
hover, năng lượng, biến thể A/B, phát hiện trường dữ liệu bị sửa, toán tử bảo toàn
hoán vị, ngân sách chính xác, tái lập seed và cả ba thuật toán trên fixture nhỏ.
Toàn bộ 112 instance được kiểm tra cận tổng tải với cấu hình gốc.

`scripts/evaluate.py` hiện có vẫn dùng được để đọc đầu ra, nhưng chưa thay đổi
trong phần việc này. Script hiện chuẩn hóa theo mỗi front cộng reference và dùng
điểm HV chuẩn hóa (1.1,1.1), khác quy trình trong `docs/evaluation.md`. Cần thống
nhất trước thí nghiệm chính thức. Chỉ xây reference từ các kết quả **cùng một
instance**, không gộp 112 instance vào một reference front.

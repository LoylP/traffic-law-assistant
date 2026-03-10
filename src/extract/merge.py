import os

dir_txt = "KG/data/raw_txt/"
dir_out = "KG/data/processed/"


def read_lines(file):
    with open(os.path.join(dir_txt, file), encoding="utf-8") as f:
        return f.read().splitlines()


# ========================
# Nghị định 100
# ========================

lines_100_1 = read_lines("nghi_dinh_100_1.txt")
lines_100_2 = read_lines("nghi_dinh_100_2.txt")

# xoá dòng đầu tiên của file 2
lines_100_2 = lines_100_2[1:]

lines_100 = lines_100_1 + lines_100_2

with open(os.path.join(dir_out, "nghi_dinh_100.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines_100))


# ========================
# Nghị định 123
# ========================

lines_123_1 = read_lines("nghi_dinh_123_1.txt")
lines_123_2 = read_lines("nghi_dinh_123_2.txt")

lines_123 = lines_123_1 + lines_123_2

start = None
end = None

for i, line in enumerate(lines_123):

    if line.startswith("Điều 2.") and start is None:
        start = i

    if line.startswith("Điều 3."):
        end = i
        break

lines_123 = lines_123[start:end]

with open(os.path.join(dir_out, "nghi_dinh_123.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines_123))


# ========================
# Nghị định 168
# ========================

lines_168_1 = read_lines("nghi_dinh_168_1.txt")
lines_168_2 = read_lines("nghi_dinh_168_2.txt")

# fix Chương III thứ 2
chuong_count = 0

for i, line in enumerate(lines_168_2):

    if line.startswith("Chương III"):
        chuong_count += 1

        if chuong_count == 2:
            lines_168_2[i-1] += " " + line
            lines_168_2.pop(i)
            break

lines_168 = lines_168_1 + lines_168_2

with open(os.path.join(dir_out, "nghi_dinh_168.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines_168))


print("Done: created 3 nghị định files")
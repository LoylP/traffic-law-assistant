import pdfplumber
import re

dir_input = "KG/data/raw_pdf/"
dir_output = "KG/data/raw_txt/"

files = {
    "2020_21 + 22_100-2019-NĐ-CP.pdf": "nghi_dinh_100_1.txt",
    "2020_23 + 24_100-2019-NĐ-CP.pdf": "nghi_dinh_100_2.txt",
    "2022_45 + 46_123-2021-NĐ-CP.pdf": "nghi_dinh_123_1.txt",
    "2022_47 + 48_123-2021-NĐ-CP.pdf": "nghi_dinh_123_2.txt",
    "2025_75 + 76_168-2024-NĐ-CP.pdf": "nghi_dinh_168_1.txt",
    "2025_77 + 78_168-2024-NĐ-CP.pdf": "nghi_dinh_168_2.txt",
}

start_pattern = re.compile(
    r"^(Chương|Mục|Điều\s+\d+[a-zđ]?\.|\d+\.\s|[a-zđ]\)|\d+[a-zđ]|“Mục|“Điều|“\d+\.|“[a-zđ]\)|“\d+[a-zđ].)"
)

congbao_pattern = re.compile(r"CÔNG\s*BÁO")
footer_continue_pattern = re.compile(r"\(Xem tiếp Công báo")
slash_pattern = re.compile(r"/\.")

for input_pdf, output_txt in files.items():

    lines = []

    with pdfplumber.open(dir_input + input_pdf) as pdf:
        for page in pdf.pages:

            text = page.extract_text()

            if not text:
                continue

            for line in text.split("\n"):

                # nếu gặp "(Xem tiếp Công báo" → bỏ toàn bộ phần dưới trang
                if footer_continue_pattern.search(line):
                    break

                # remove CÔNG BÁO header
                if congbao_pattern.search(line):
                    continue

                # nếu có "/." → cắt tại đó nhưng vẫn giữ phần trước
                if "/." in line:
                    line = line.split("/.", 1)[0]

                clean = line.strip()

                if clean:
                    lines.append(clean)

    # remove everything before "Chương" hoặc "(Tiếp theo Công báo"
    start_index = 0

    for i, line in enumerate(lines):

        if line.startswith("Chương"):
            start_index = i
            break

        if line.startswith("(Tiếp theo Công báo"):
            start_index = i + 1
            break

    lines = lines[start_index:]

    # merge lines
    merged_lines = []

    for line in lines:

        if not merged_lines:
            merged_lines.append(line)
            continue

        if start_pattern.match(line):
            merged_lines.append(line)
        else:
            merged_lines[-1] += " " + line

    with open(dir_output + output_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(merged_lines))

    print(f"Done: {input_pdf} → {output_txt}")
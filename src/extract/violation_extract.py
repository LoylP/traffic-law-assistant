import os
import re
import json

dir_input = "data/processed/"
dir_output = "data/structured/"
FILE_PATH = "nghi_dinh_168.txt"

DECREE = "NĐ 168/2024/NĐ-CP"

vehicle_keywords = [
    "xe ô tô",
    "xe mô tô",
    "xe gắn máy",
    "xe thô sơ",
    "xe đạp",
    "xe đạp máy",
    "xe cơ giới",
    "máy kéo",
    "xe máy chuyên dùng",
    "xe vệ sinh môi trường",
    "xe cứu hộ",
    "xe cứu thương",
    "đi bộ",
    "dẫn dắt vật nuôi"
]


# =====================================================
# Money
# =====================================================

def normalize_money(v):
    return int(v.replace(".", ""))


def extract_fine(text):

    m = re.search(r"từ\s+([\d\.]+)\s+đồng\s+đến\s+([\d\.]+)\s+đồng", text)

    if m:
        return normalize_money(m.group(1)), normalize_money(m.group(2))

    return None, None


# =====================================================
# Vehicle extract
# =====================================================

def extract_vehicle_from_dieu(text):

    text = text.lower()

    for v in vehicle_keywords:
        if v in text:
            return v

    return "khác"


def extract_vehicle_from_khoan(text):

    text = text.lower()

    m = re.search(r"đối với người\s+(.+?)\s+thực hiện", text)

    if m:

        candidate = m.group(1).strip()

        for v in vehicle_keywords:
            if v in candidate:
                return v

    return "khác"


# =====================================================
# Clean description
# =====================================================

def remove_point_prefix(text):
    return re.sub(r"^[a-zđ]\)\s*", "", text)


def remove_khoan_prefix(text):
    return re.sub(r"^\d+\.\s*", "", text)


def clean_description(text):

    text = remove_point_prefix(text)

    text = remove_khoan_prefix(text)

    text = re.sub(r"trừ.+", "", text)

    text = text.strip()

    text = text.rstrip(",;.")

    return text


# =====================================================
# Extract Chapter II
# =====================================================

def extract_chapter_2(text):

    start = text.find("Chương II")

    end = text.find("Chương III")

    if start == -1:
        raise Exception("Không tìm thấy Chương II")

    if end == -1:
        return text[start:]

    return text[start:end]


# =====================================================
# Parse structure
# =====================================================

def parse_structure(lines):

    data = {}

    current_dieu = None
    current_khoan = None

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # =========================
        # Điều
        # =========================

        dieu_match = re.match(r"Điều\s+(\d+)", line)

        if dieu_match:

            current_dieu = dieu_match.group(1)

            vehicle = extract_vehicle_from_dieu(line)

            data[current_dieu] = {
                "vehicle": vehicle,
                "khoan": {}
            }

            continue

        # =========================
        # Khoản
        # =========================

        khoan_match = re.match(r"(\d+)\.", line)

        if khoan_match and current_dieu:

            current_khoan = khoan_match.group(1)

            vehicle = extract_vehicle_from_khoan(line)

            if vehicle == "khác":
                vehicle = data[current_dieu]["vehicle"]

            data[current_dieu]["khoan"][current_khoan] = {
                "text": line,
                "vehicle": vehicle,
                "points": {}
            }

            continue

        # =========================
        # Điểm
        # =========================

        point_match = re.match(r"([a-zđ])\)", line)

        if point_match and current_dieu and current_khoan:

            p = point_match.group(1)

            vehicle = data[current_dieu]["khoan"][current_khoan]["vehicle"]

            data[current_dieu]["khoan"][current_khoan]["points"][p] = {
                "text": line,
                "vehicle": vehicle
            }

    return data


# =====================================================
# Build JSON
# =====================================================

def build_json(tree):

    results = []

    vid = 1

    for dieu in tree:

        for khoan in tree[dieu]["khoan"]:

            kdata = tree[dieu]["khoan"][khoan]

            fine_min, fine_max = extract_fine(kdata["text"])

            vehicle = kdata["vehicle"]

            if kdata["points"]:

                for p in kdata["points"]:

                    pdata = kdata["points"][p]

                    text = pdata["text"]

                    desc = clean_description(text)

                    record = {
                        "violation_id": f"V{vid:04d}",
                        "description_natural": desc,
                        "normalized_violation": desc,
                        "vehicle_type": vehicle,
                        "context_condition": "",
                        "fine_min": fine_min,
                        "fine_max": fine_max,
                        "additional_sanctions": "",
                        "legal_basis": f"{DECREE}, Điều {dieu} Khoản {khoan} Điểm {p}",
                        "confidence_label": ""
                    }

                    results.append(record)

                    vid += 1

            else:

                desc = clean_description(kdata["text"])

                record = {
                    "violation_id": f"V{vid:04d}",
                    "description_natural": desc,
                    "normalized_violation": desc,
                    "vehicle_type": vehicle,
                    "context_condition": "",
                    "fine_min": fine_min,
                    "fine_max": fine_max,
                    "additional_sanctions": "",
                    "legal_basis": f"{DECREE}, Điều {dieu} Khoản {khoan}",
                    "confidence_label": ""
                }

                results.append(record)

                vid += 1

    return results


# =====================================================
# MAIN
# =====================================================

def main():

    os.makedirs(dir_output, exist_ok=True)

    with open(os.path.join(dir_input, FILE_PATH), "r", encoding="utf-8") as f:
        text = f.read()

    chap2 = extract_chapter_2(text)

    lines = chap2.split("\n")

    tree = parse_structure(lines)

    results = build_json(tree)

    with open(os.path.join(dir_output, "violations_168.json"), "w", encoding="utf-8") as f:

        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Extracted {len(results)} violations")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_spelling.py - Sửa lỗi chính tả/OCR trong các file Nghị định

Danh sách lỗi phổ biến từ OCR được sửa tự động.
"""

import re
from pathlib import Path

# Mapping: lỗi → đúng
SPELLING_FIXES = {
    # Lỗi từ ND168
    "Hanh phúc": "Hạnh phúc",
    "Tà chức": "Tổ chức",
    "Tả chức": "Tổ chức",
    "nam 2020": "năm 2020",
    "nam 2019": "năm 2019",
    "nam 2024": "năm 2024",
    "nam 2021": "năm 2021",
    "thang 6": "tháng 6",
    "I1 năm": "11 năm",
    "dé nghị": "đề nghị",
    "dê quản": "để quản",
    "dê xử": "để xử",
    "dê làm": "để làm",
    "dê rút": "để rút",
    "dé cấp": "để cấp",
    "dê cứu": "để cứu",
    "dê đóng": "để đóng",
    "vệ trật": "về trật",
    "quản ly": "quản lý",
    "lãnh thô": "lãnh thổ",
    "tô chức": "tổ chức",
    "cô phan": "cổ phần",
    
    # Lỗi về từ tiếng Anh và kỹ thuật
    "gidi": "giới",
    "san xuat": "sản xuất",
    "lắp rap": "lắp ráp",
    "rap": "ráp",
    "khâu": "khẩu",
    "ban hành": "ban hành",
    "chứng nhận": "chứng nhận",
    "tim": "dò tìm",
    "tám": "tám",
    
    # Lỗi chung cho cả 3 file
    "cỗ phân": "cổ phần",
    "von đầu tư": "vốn đầu tư",
    "chuyền": "chuyển",
    "römoóc": "rơ-moóc",
    "ro moóc": "rơ-moóc",
    "romooc": "rơ-moóc",
    "rômoóc": "rơ-moóc",
    "thê tháo": "thể tháo",
    "phan đầu": "phần đầu",
    "lap trên": "lắp trên",
    "chạy băng": "chạy bằng",
    "xát xi": "sát xi",
    "có phân động": "có phần động",
    "diém": "điểm",
    "diem": "điểm",
    "khoán": "khoản",
    
    # Lỗi từ ND123 & ND168 khác
    "hành chỉnh": "hành chính",
    "cơng ty": "công ty",
    "xư phạt": "xử phạt",
    "xư lý": "xử lý",
}

def fix_file(input_path: str, output_path: str = None) -> int:
    """
    Sửa lỗi chính tả trong file.
    
    Returns: số lỗi được sửa
    """
    if output_path is None:
        output_path = input_path
    
    # Đọc file
    with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    
    original_text = text
    fix_count = 0
    
    # Áp dụng các sửa fix
    for wrong, correct in SPELLING_FIXES.items():
        # Case-insensitive replacement
        pattern = re.compile(re.escape(wrong), re.IGNORECASE)
        
        # Đếm số match
        matches = len(pattern.findall(text))
        if matches > 0:
            print(f"  ✓ {wrong:20} → {correct:20} ({matches} lần)")
            fix_count += matches
        
        # Thay thế (giữ case)
        text = pattern.sub(correct, text)
    
    # Ghi file nếu có thay đổi
    if text != original_text:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"\n✅ Lưu: {output_path} ({fix_count} lỗi được sửa)")
    else:
        print(f"\n⚠️  Không tìm thấy lỗi để sửa")
    
    return fix_count

def main():
    print("=" * 70)
    print("FIX SPELLING - Sửa Lỗi Chính Tả/OCR")
    print("=" * 70)
    
    # Fix ND100
    print("\n📄 Xử lý ND100_02.txt...")
    fix_file("../../data/raw/ND100_02.txt")
    
    # # Fix ND123
    # print("\n📄 Xử lý ND123.txt...")
    # fix_file("ND123.txt")
    
    # # Fix ND168
    # print("\n📄 Xử lý ND168.txt...")
    # fix_file("ND168.txt")
    
    # print("\n" + "=" * 70)
    # print("✅ Hoàn thành!")
    # print("=" * 70)

if __name__ == "__main__":
    main()

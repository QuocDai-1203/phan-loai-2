"""gold_annotations.py - dap an huong trang do MO HINH (Claude) xem to tiep xuc va ghi tay, KHONG phai nguoi.

Cach doc: `idx` la so thu tu trong `sample_pages.csv` (sinh boi make_sheets.py voi seed ghi trong RESULTS.md).
Huong = so do xoay NGUOC chieu kim dong ho can ap len anh GOC (anh engine nhin thay, chua xoay) de chu thang dung,
cung quy uoc voi co `rotated_90/180/270` cua src/ocr (np.rot90 k = do/90). Tuc la chu doc tu DUOI len tren => 270,
chu doc tu TREN xuong duoi => 90, chu lon nguoc => 180, thang => 0.
Trang "gan trong": trang gan nhu khong co chu/hoa van (trang trang, chi co vet den cua may scan, vai dong le): huong
khong xac dinh; ghi huong 0 va co `blank=1`, khi tinh do chinh xac huong cac trang nay duoc tach rieng.
Cach xac dinh chu yeu: huong doc cua cac dong chu in (o thumbnail dong chu dai: dau dong dong deu o phia nao; so thu tu muc
"1. 2. 3." o dau dong; tieu de; khoi chu ky / logo) va phong to bang zoom_sheets.py khi mo ho. Cac trang kho (26, 30, 31, 33,
bang PCCC tren thumbnail; trang 30 ban dau bi doc nham la 0, doi thanh 180 sau khi cat vung nhan ban ve va doi chieu voi ocr_v2) da xem lai o do phan giai cao hon.
"""
BLANK = {1, 2, 3, 4, 5, 6, 7, 40, 62, 71, 73, 75, 94, 96, 98, 126, 128, 130, 134, 143, 145, 147, 161, 167, 169, 171, 173,
         183, 192, 194, 206, 215, 217, 219, 221, 223, 225, 242, 252, 314, 327}
ROT_270 = {8, 10, 11, 13, 14, 15, 16, 17, 18, 20, 21, 23, 25, 27, 28, 29, 32, 33, 34, 36, 37, 39}
ROT_90 = {9, 12, 19, 22, 24, 26, 31, 35, 38}
ROT_180 = {30}   # ban ve: nhan 'BICH NOI', 'BAC TREN' lon nguoc (xem lai o cat vung; ban dau doc nham tieu de la thang)
# moi trang con lai (41-353 tru trang trang) la 0.


def gold_orientation(idx: int) -> int:
    if idx in ROT_270:
        return 270
    if idx in ROT_90:
        return 90
    if idx in ROT_180:
        return 180
    return 0


def is_blank(idx: int) -> bool:
    return idx in BLANK

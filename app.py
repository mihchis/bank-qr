from flask import Flask, render_template, request, send_file
import os
import re
from bankqr import VietQR, get_bin_code, get_bank_name, generate_qr_code, bank_list

# Tạo ảnh tổng hợp gồm QR và đầy đủ thông tin chuyển khoản
def create_payment_image(qr_path, bank_name, account_number, amount, purpose, output_path):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        # Nếu PIL không khả dụng, bỏ qua tạo ảnh tổng hợp
        return

    # Thiết lập kích thước và màu sắc
    width, height = 1200, 700
    margin = 40
    bg_color = (255, 255, 255)
    card_color = (247, 250, 255)
    text_color = (33, 43, 54)
    accent_color = (25, 118, 210)

    # Tạo nền
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Vẽ header
    def load_font(size):
        try:
            return ImageFont.truetype("arial.ttf", size)
        except Exception:
            try:
                return ImageFont.truetype("DejaVuSans.ttf", size)
            except Exception:
                return ImageFont.load_default()

    title_font = load_font(36)
    label_font = load_font(28)
    value_font = load_font(30)
    small_font = load_font(20)

    draw.text((margin, margin), "Thông tin chuyển khoản", fill=accent_color, font=title_font)

    # Khu vực card
    card_top = margin + 60
    card_left = margin
    card_right = width - margin
    card_bottom = height - margin
    draw.rectangle([card_left, card_top, card_right, card_bottom], fill=card_color)

    # Mở QR và đặt bên trái
    try:
        qr_img = Image.open(qr_path).convert('RGB')
    except Exception:
        return

    qr_size = 480
    qr_img = qr_img.resize((qr_size, qr_size), Image.NEAREST)
    qr_x = card_left + 50
    qr_y = card_top + 50
    img.paste(qr_img, (qr_x, qr_y))

    # Gợi ý quét mã
    draw.text((qr_x + 80, qr_y + qr_size + 20), "Quét mã để thanh toán", fill=accent_color, font=small_font)

    # Thông tin bên phải
    info_x = qr_x + qr_size + 70
    info_y = qr_y
    line_gap = 70

    def draw_info(label, value, y):
        draw.text((info_x, y), label, fill=text_color, font=label_font)
        draw.text((info_x + 240, y), value, fill=text_color, font=value_font)

    # Định dạng số tiền
    amount_text = f"{int(amount):,}".replace(",", ".") + " VND"

    draw_info("Ngân hàng:", bank_name, info_y)
    draw.line([(info_x, info_y + 45), (card_right - 50, info_y + 45)], fill=(225, 230, 240), width=2)
    draw_info("Số tài khoản:", account_number, info_y + line_gap)
    draw.line([(info_x, info_y + line_gap + 45), (card_right - 50, info_y + line_gap + 45)], fill=(225, 230, 240), width=2)
    draw_info("Số tiền:", amount_text, info_y + 2 * line_gap)
    draw.line([(info_x, info_y + 2 * line_gap + 45), (card_right - 50, info_y + 2 * line_gap + 45)], fill=(225, 230, 240), width=2)
    draw_info("Nội dung:", purpose if purpose else "", info_y + 3 * line_gap)

    # Lưu ảnh
    img.save(output_path, format='PNG')

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    qr_image = None
    bank_info = None
    error_message = None
    
    if request.method == 'POST':
        try:
            identifier = request.form['bank']
            # Làm sạch số tài khoản và số tiền: chỉ giữ chữ số
            account_number_raw = request.form['account_number']
            amount_raw = request.form['amount']
            account_number = re.sub(r"\D", "", account_number_raw)
            amount = re.sub(r"\D", "", amount_raw)
            purpose = request.form['purpose']
            
            viet_qr = VietQR()
            bin_code = get_bin_code(identifier, bank_list)
            viet_qr.set_beneficiary_organization(bin_code, account_number)
            viet_qr.set_transaction_amount(amount)
            viet_qr.set_additional_data_field_template(purpose)
            qr_data = viet_qr.build()
            
            # Tạo tên file QR duy nhất dựa trên thời gian
            qr_filename = f"static/qr_{account_number}.png"
            
            # Đảm bảo thư mục static tồn tại
            os.makedirs('static', exist_ok=True)
            
            # Tạo mã QR
            generate_qr_code(qr_data, qr_filename)
            
            bank_name = get_bank_name(bin_code, bank_list)
            bank_info = {
                'bank_name': bank_name,
                'account_number': account_number,
                'amount': amount,
                'purpose': purpose,
                'qr_data': qr_data,
                'qr_image': qr_filename
            }

            # Tạo ảnh tổng hợp để tải về
            poster_filename = f"static/payment_{account_number}.png"
            create_payment_image(qr_filename, bank_name, account_number, amount, purpose, poster_filename)
            bank_info['poster_image'] = poster_filename
            
        except ValueError as e:
            error_message = f"Lỗi: {e}"
    
    return render_template('index.html', banks=bank_list, bank_info=bank_info, error_message=error_message)

if __name__ == '__main__':
    app.run(debug=True)
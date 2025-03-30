from flask import Flask, render_template, request, send_file, jsonify
import os
import subprocess
import time
import uuid
import zipfile
import shutil
from app2 import chat_bp  # Import the blueprint from app2.py

app = Flask(__name__)

# Register the blueprint for the chat routes
app.register_blueprint(chat_bp, url_prefix='/chat')

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'m4s', 'mp3', 'wav', 'flac', 'ogg'}

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/tool/m4s')
def tool_m4s():
    return render_template('tool_m4s.html')


@app.route('/tool/audio-separator')
def tool_audio_separator():
    return render_template('tool_audio_separator.html')


@app.route('/convert', methods=['POST'])
def convert():
    try:
        if 'file' not in request.files:
            return "未选择文件", 400
        file = request.files['file']
        if file.filename == '':
            return "未选择文件", 400
        if not allowed_file(file.filename):
            return "仅支持.m4s文件", 400

        unique_id = str(uuid.uuid4())
        input_filename = f"input_{unique_id}.m4s"
        output_filename = f"output_{unique_id}.mp3"

        input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

        file.save(input_path)
        if not os.path.exists(input_path):
            raise Exception("文件保存失败")

        try:
            subprocess.run(
                ['ffmpeg', '-i', input_path, '-vn', '-acodec', 'libmp3lame', '-q:a', '2', output_path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30  # 30秒超时
            )
        except subprocess.TimeoutExpired:
            return "转换超时，请重试", 500

        response = send_file(
            output_path,
            as_attachment=True,
            download_name=output_filename
        )

        @response.call_on_close
        def cleanup():
            time.sleep(5)
            try:
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(output_path):
                    os.remove(output_path)
            except Exception as e:
                print(f"清理失败: {str(e)}")

        return response

    except subprocess.CalledProcessError as e:
        return f"FFmpeg错误: {e.stderr.decode('utf-8')}", 500
    except Exception as e:
        return f"系统错误: {str(e)}", 500


@app.route('/separate-audio', methods=['POST'])
def separate_audio():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "未选择文件"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "未选择文件"}), 400

        # 检查文件类型
        if not file.filename.lower().endswith(('.mp3', '.wav', '.flac', '.ogg')):
            return jsonify({"error": "仅支持 MP3, WAV, FLAC 和 OGG 格式"}), 400

        # 创建唯一ID和文件路径
        unique_id = str(uuid.uuid4())
        input_filename = f"input_{unique_id}{os.path.splitext(file.filename)[1]}"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)

        # 保存上传的文件
        file.save(input_path)

        # 创建输出目录
        output_dir = os.path.join(app.config['UPLOAD_FOLDER'], f"output_{unique_id}")
        os.makedirs(output_dir, exist_ok=True)

        # 使用Demucs分离音频为人声和伴奏
        # 设置环境变量以确保torchaudio使用正确的后端
        my_env = os.environ.copy()
        my_env["TORCHAUDIO_USE_SOUNDFILE_LEGACY"] = "1"

        # 运行Demucs命令
        try:
            # 使用htdemucs模型，只分离人声和伴奏
            subprocess.run(
                ['demucs', '--two-stems=vocals', '-n', 'htdemucs', input_path, '-o', output_dir],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=my_env,
                timeout=300  # 5分钟超时
            )
        except subprocess.CalledProcessError as e:
            return jsonify({"error": f"Demucs错误: {e.stderr.decode('utf-8')}"}), 500

        # Demucs输出目录结构: output_dir/htdemucs/input_filename/[vocals.wav, no_vocals.wav]
        model_dir = os.path.join(output_dir, "htdemucs")
        track_dir = os.path.join(model_dir, os.path.splitext(input_filename)[0])

        vocals_path = os.path.join(track_dir, "vocals.wav")
        no_vocals_path = os.path.join(track_dir, "no_vocals.wav")

        # 检查文件是否存在
        if not os.path.exists(vocals_path) or not os.path.exists(no_vocals_path):
            return jsonify({"error": "分离失败，未生成输出文件"}), 500

        # 准备下载链接
        track_files = {
            "vocals": f"/download/{unique_id}/vocals",
            "instrumental": f"/download/{unique_id}/instrumental"
        }

        # 存储会话数据，以便下载路由可以找到文件
        app.config[f'SEPARATION_{unique_id}'] = {
            'output_dir': output_dir,
            'track_dir': track_dir,
            'input_path': input_path,
            'created_at': time.time()
        }

        return jsonify(track_files)

    except subprocess.TimeoutExpired:
        return jsonify({"error": "处理超时，请尝试更短的音频文件"}), 500
    except Exception as e:
        return jsonify({"error": f"系统错误: {str(e)}"}), 500


@app.route('/download/<unique_id>/<track_type>', methods=['GET'])
def download_track(unique_id, track_type):
    try:
        # 获取会话数据
        session_data = app.config.get(f'SEPARATION_{unique_id}')
        if not session_data:
            return "文件不存在或已过期", 404

        track_dir = session_data['track_dir']

        # 验证轨道类型
        if track_type == 'vocals':
            track_path = os.path.join(track_dir, "vocals.wav")
            download_name = f"vocals_{unique_id}.wav"
        elif track_type == 'instrumental':
            track_path = os.path.join(track_dir, "no_vocals.wav")
            download_name = f"instrumental_{unique_id}.wav"
        else:
            return "无效的轨道类型", 400

        if not os.path.exists(track_path):
            return "轨道文件不存在", 404

        # 发送文件
        return send_file(
            track_path,
            as_attachment=True,
            download_name=download_name
        )

    except Exception as e:
        return f"下载错误: {str(e)}", 500


# 定期清理临时文件
def cleanup_temp_files():
    current_time = time.time()
    keys_to_remove = []

    # 查找过期的会话
    for key, data in app.config.items():
        if key.startswith('SEPARATION_'):
            if current_time - data['created_at'] > 3600:  # 1小时后过期
                # 删除文件
                try:
                    if os.path.exists(data['output_dir']):
                        shutil.rmtree(data['output_dir'])
                    if os.path.exists(data['input_path']):
                        os.remove(data['input_path'])
                except Exception as e:
                    print(f"清理失败: {str(e)}")

                keys_to_remove.append(key)

    # 从配置中移除过期会话
    for key in keys_to_remove:
        del app.config[key]


if __name__ == '__main__':
    import threading
    import time


    # 启动清理线程
    def cleanup_thread():
        while True:
            time.sleep(300)  # 每5分钟检查一次
            with app.app_context():
                cleanup_temp_files()


    threading.Thread(target=cleanup_thread, daemon=True).start()

    app.run(debug=True, port=5000)
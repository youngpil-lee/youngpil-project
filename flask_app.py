from app import create_app

app = create_app()

if __name__ == '__main__':
    # .env 파일에서 포트 설정을 읽어오거나 기본값 5001 사용
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    port = int(os.getenv('FLASK_PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    
    print(f" * Starting Flask server on port {port} (debug={debug})")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        use_reloader=False # 중복 실행 방지
    )

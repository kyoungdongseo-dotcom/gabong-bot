import json
import os

CONFIG_FILE = 'config.json'

def load_config():
    """config.json 파일을 로드합니다. 파일이 없으면 빈 딕셔너리를 반환합니다."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"config.json 파싱 오류: {e}")
            return {}
    else:
        print("config.json 파일이 존재하지 않습니다.")
        return {}

def save_config(config_data):
    """config.json 파일에 데이터를 저장합니다."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        print("config.json이 성공적으로 저장되었습니다.")
    except Exception as e:
        print(f"config.json 저장 오류: {e}")

def get(key, default=None):
    """설정 값 가져오기. 키가 없으면 기본값 반환."""
    config = load_config()
    return config.get(key, default)

def set_value(key, value):
    """설정 값 설정 및 저장."""
    config = load_config()
    config[key] = value
    save_config(config)

def validate_config():
    """필수 설정 키 검증."""
    required_keys = ['telegram_token', 'group_id', 'admin_ids']
    config = load_config()
    
    print("\n🔍 설정 검증 중...")
    errors = []
    
    for key in required_keys:
        if key not in config or not config[key]:
            errors.append(f"  ❌ {key}: 누락됨")
        else:
            print(f"  ✅ {key}: 설정됨")
    
    if errors:
        print("\n⚠️  필수 설정 오류:")
        for error in errors:
            print(error)
        raise ValueError(f"필수 설정 누락: {[k for k in required_keys if k not in config]}")
    
    print("✅ 모든 필수 설정 OK\n")
    return True

# 전역 설정 캐시 (성능 최적화)
_config_cache = None

def get_cached(key, default=None):
    """캐시된 설정 값 가져오기. 없으면 로드 후 캐시."""
    global _config_cache
    if _config_cache is None:
        _config_cache = load_config()
    return _config_cache.get(key, default)

def reload_cache():
    """설정 캐시 리로드."""
    global _config_cache
    _config_cache = load_config()
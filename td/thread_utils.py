import random
import string


def generate_random_name(length=32):
    """
    生成一个由大小写字母和下划线组成的随机字符串

    Args:
        length: 字符串长度，默认32

    Returns:
        随机生成的字符串
    """
    # 定义可用字符: 大小写字母和下划线
    characters = string.ascii_uppercase + string.ascii_lowercase + '_'
    # 随机选择指定长度的字符并拼接
    return ''.join(random.choice(characters) for _ in range(length))
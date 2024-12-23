#!/usr/bin/env python
import os
import sys

def main():
    """Основная функция для управления Django проектом."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flower_delivery.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Не удалось импортировать Django. Убедитесь, что Django установлен и "
            "находится в вашем виртуальном окружении."
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()

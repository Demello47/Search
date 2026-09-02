#!/usr/bin/env python3
"""
Скрипт: переименование файлов/папок по списку из текстового файла.

Логика:
1. Читает текстовый файл, где каждая строка — это название (в нужном порядке).
2. Ищет в указанной папке файл или подпапку с таким названием
   (сравнение без учёта регистра; для файлов расширение игнорируется).
3. Если найдено — переименовывает в формат "N_название" (N — номер строки,
   считая с 1), сохраняя расширение файла, если это файл.
4. Если НЕ найдено — создаёт в этой папке пустой файл с именем "N_название.txt".
5. В конце выводит отчёт: что переименовано, а что было создано как отсутствующее.

Использование:
    python rename_by_list.py путь_к_списку.txt путь_к_папке

Если аргументы не переданы, скрипт запросит их в консоли.
"""

import os
import sys


def read_names(list_file: str) -> list[str]:
    with open(list_file, "r", encoding="utf-8-sig") as f:
        names = [line.strip() for line in f if line.strip()]
    return names


def build_index(folder: str) -> dict[str, str]:
    """
    Строит словарь: ключ - имя без расширения (в нижнем регистре),
    значение - реальное имя файла/папки в директории.
    """
    index = {}
    for entry in os.listdir(folder):
        full_path = os.path.join(folder, entry)
        if os.path.isdir(full_path):
            key = entry.lower()
        else:
            key = os.path.splitext(entry)[0].lower()
        index[key] = entry
    return index


def main():
    if len(sys.argv) == 3:
        list_file = sys.argv[1]
        folder = sys.argv[2]
    else:
        list_file = input("Путь к текстовому файлу со списком названий: ").strip().strip('"')
        folder = input("Путь к папке, в которой переименовывать: ").strip().strip('"')

    if not os.path.isfile(list_file):
        print(f"Ошибка: файл со списком не найден: {list_file}")
        return

    if not os.path.isdir(folder):
        print(f"Ошибка: папка не найдена: {folder}")
        return

    names = read_names(list_file)
    if not names:
        print("Файл со списком пуст.")
        return

    index = build_index(folder)

    renamed = []
    created = []

    for i, name in enumerate(names, start=1):
        key = name.lower()
        if key in index:
            real_name = index[key]
            real_path = os.path.join(folder, real_name)

            if os.path.isdir(real_path):
                new_name = f"{i}_{real_name}"
            else:
                base, ext = os.path.splitext(real_name)
                new_name = f"{i}_{base}{ext}"

            new_path = os.path.join(folder, new_name)

            if os.path.exists(new_path):
                print(f"[Пропущено] Целевое имя уже существует: {new_name}")
                continue

            os.rename(real_path, new_path)
            renamed.append((name, new_name))
            print(f"[Переименовано] {real_name}  ->  {new_name}")
        else:
            # Не найдено - создаём пустой файл
            new_name = f"{i}_{name}.txt"
            new_path = os.path.join(folder, new_name)
            with open(new_path, "w", encoding="utf-8"):
                pass
            created.append((name, new_name))
            print(f"[Не найдено] '{name}' отсутствовал в папке -> создан пустой файл {new_name}")

    print("\n--- ИТОГ ---")
    print(f"Переименовано: {len(renamed)}")
    print(f"Не найдено (создано пустых файлов): {len(created)}")

    if created:
        print("\nСписок отсутствовавших названий:")
        for name, new_name in created:
            print(f"  - {name}  (создан как {new_name})")


if __name__ == "__main__":
    main()

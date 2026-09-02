#!/usr/bin/env python3
"""
Скрипт: переименование файлов/папок по списку из текстового файла.
ВЕРСИЯ 2 - безопасно продолжает работу, если часть папок уже была
переименована в предыдущем (сломавшемся) запуске.

Логика:
1. Читает текстовый файл со списком названий по порядку.
2. Для каждого элемента в папке определяет "чистое" имя:
   - если имя уже имеет вид "N_название" (где N - число) - чистое имя
     это то, что после первого подчёркивания;
   - иначе чистое имя - это само имя (без расширения, если это файл).
3. Ищет совпадение чистого имени с названием из списка.
4. Если найдено и папка/файл ЕЩЁ НЕ переименован(а) правильно (т.е. не
   имеет уже нужного префикса N_) - переименовывает.
5. Если найдено и уже переименовано правильно - пропускает (ничего не делает).
6. Если не найдено вообще (ни в исходном, ни в переименованном виде) -
   создаёт пустой файл "N_название.txt".
7. В конце - подробный отчёт.

Использование:
    python rename_by_list_v2.py путь_к_списку.txt путь_к_папке
"""

import os
import re
import sys

PREFIX_RE = re.compile(r"^(\d+)_(.+)$")


def read_names(list_file: str) -> list[str]:
    with open(list_file, "r", encoding="utf-8-sig") as f:
        names = [line.strip() for line in f if line.strip()]
    return names


def clean_key(entry: str, is_dir: bool):
    """
    Возвращает (ключ_для_сравнения_в_нижнем_регистре, существующий_номер_если_есть).
    Для файлов расширение отбрасывается перед проверкой на префикс.
    """
    base = entry if is_dir else os.path.splitext(entry)[0]
    m = PREFIX_RE.match(base)
    if m:
        return m.group(2).lower(), int(m.group(1))
    return base.lower(), None


def build_index(folder: str):
    """
    Строит словарь: ключ (чистое имя, нижний регистр) -> инфо о реальном элементе.
    """
    index = {}
    for entry in os.listdir(folder):
        full_path = os.path.join(folder, entry)
        is_dir = os.path.isdir(full_path)
        key, existing_num = clean_key(entry, is_dir)
        index[key] = {
            "real_name": entry,
            "is_dir": is_dir,
            "existing_num": existing_num,
        }
    return index


def main():
    if len(sys.argv) == 3:
        list_file = sys.argv[1]
        folder = sys.argv[2]
    else:
        list_file = input("Путь к текстовому файлу со списком названий: ").strip().strip('"')
        folder = input("Путь к папке: ").strip().strip('"')

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

    already_ok = []
    renamed = []
    created = []
    errors = []

    for i, name in enumerate(names, start=1):
        key = name.lower()
        info = index.get(key)

        if info is None:
            # Не найдено вообще - создаём пустой файл
            new_name = f"{i}_{name}.txt"
            new_path = os.path.join(folder, new_name)
            if os.path.exists(new_path):
                print(f"[Уже есть] {new_name} - пропущено")
                continue
            try:
                with open(new_path, "w", encoding="utf-8"):
                    pass
                created.append((name, new_name))
                print(f"[Не найдено] '{name}' -> создан пустой файл {new_name}")
            except Exception as e:
                errors.append((name, str(e)))
                print(f"[ОШИБКА] '{name}': {e}")
            continue

        if info["existing_num"] == i:
            # Уже переименовано правильно - ничего не делаем
            already_ok.append(name)
            print(f"[Уже готово] {info['real_name']} - пропущено")
            continue

        # Нужно переименовать (или перепереименовать с правильным номером)
        real_path = os.path.join(folder, info["real_name"])
        if info["is_dir"]:
            new_name = f"{i}_{name}"
        else:
            ext = os.path.splitext(info["real_name"])[1]
            new_name = f"{i}_{name}{ext}"
        new_path = os.path.join(folder, new_name)

        if os.path.exists(new_path) and new_path != real_path:
            errors.append((name, f"целевое имя уже занято: {new_name}"))
            print(f"[ОШИБКА] Не могу переименовать '{info['real_name']}' -> {new_name}: имя уже занято")
            continue

        try:
            os.rename(real_path, new_path)
            renamed.append((name, info["real_name"], new_name))
            print(f"[Переименовано] {info['real_name']}  ->  {new_name}")
        except Exception as e:
            errors.append((name, str(e)))
            print(f"[ОШИБКА] Не могу переименовать '{info['real_name']}': {e}")

    print("\n--- ИТОГ ---")
    print(f"Уже было готово: {len(already_ok)}")
    print(f"Переименовано сейчас: {len(renamed)}")
    print(f"Не найдено (созданы пустые файлы): {len(created)}")
    print(f"Ошибок: {len(errors)}")

    if errors:
        print("\nСписок ошибок:")
        for name, err in errors:
            print(f"  - {name}: {err}")

    if created:
        print("\nСписок отсутствовавших названий:")
        for name, new_name in created:
            print(f"  - {name} (создан как {new_name})")


if __name__ == "__main__":
    main()

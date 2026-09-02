#!/usr/bin/env python3
"""
Скрипт: переименование файлов/папок по списку из текстового файла.
ВЕРСИЯ 3 - "медленная" / с подтверждением.

Отличия от v2:
- Перед КАЖДЫМ переименованием или созданием файла - спрашивает
  разрешение (y/n). Можно пропустить конкретный шаг, не прерывая весь скрипт.
- Есть пауза (задержка) между операциями, чтобы не делать много быстрых
  файловых операций подряд (это может быть причиной срабатывания
  антивируса/XDR).
- Логика поиска совпадений и определения "уже переименовано" - та же,
  что и в v2 (понимает уже проставленные префиксы N_).

Использование:
    python rename_by_list_v3_manual.py путь_к_списку.txt путь_к_папке

При запуске без аргументов - спросит пути в консоли.
"""

import os
import re
import sys
import time

PREFIX_RE = re.compile(r"^(\d+)_(.+)$")

# Пауза в секундах между операциями (можно увеличить/уменьшить)
DELAY_SECONDS = 1.5


def read_names(list_file: str) -> list[str]:
    with open(list_file, "r", encoding="utf-8-sig") as f:
        names = [line.strip() for line in f if line.strip()]
    return names


def clean_key(entry: str, is_dir: bool):
    base = entry if is_dir else os.path.splitext(entry)[0]
    m = PREFIX_RE.match(base)
    if m:
        return m.group(2).lower(), int(m.group(1))
    return base.lower(), None


def build_index(folder: str):
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


def ask_confirm(prompt: str) -> bool:
    while True:
        ans = input(f"{prompt} (y - да / n - пропустить / q - выйти): ").strip().lower()
        if ans in ("y", "yes", "д", "да"):
            return True
        if ans in ("n", "no", "н", "нет"):
            return False
        if ans in ("q", "quit"):
            print("Остановлено пользователем.")
            sys.exit(0)
        print("Не понял ответ, введите y, n или q.")


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
    skipped = []
    errors = []

    for i, name in enumerate(names, start=1):
        key = name.lower()
        info = index.get(key)

        if info is None:
            new_name = f"{i}_{name}.txt"
            new_path = os.path.join(folder, new_name)
            if os.path.exists(new_path):
                print(f"[Уже есть] {new_name} - пропущено")
                continue

            if ask_confirm(f"'{name}' не найдено в папке. Создать пустой файл {new_name}?"):
                try:
                    with open(new_path, "w", encoding="utf-8"):
                        pass
                    created.append((name, new_name))
                    print(f"[Создано] {new_name}")
                except Exception as e:
                    errors.append((name, str(e)))
                    print(f"[ОШИБКА] '{name}': {e}")
                time.sleep(DELAY_SECONDS)
            else:
                skipped.append(name)
                print(f"[Пропущено пользователем] {name}")
            continue

        if info["existing_num"] == i:
            already_ok.append(name)
            print(f"[Уже готово] {info['real_name']} - пропущено")
            continue

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

        if ask_confirm(f"Переименовать '{info['real_name']}' -> '{new_name}'?"):
            try:
                os.rename(real_path, new_path)
                renamed.append((name, info["real_name"], new_name))
                print(f"[Переименовано] {info['real_name']} -> {new_name}")
            except Exception as e:
                errors.append((name, str(e)))
                print(f"[ОШИБКА] Не могу переименовать '{info['real_name']}': {e}")
            time.sleep(DELAY_SECONDS)
        else:
            skipped.append(name)
            print(f"[Пропущено пользователем] {info['real_name']}")

    print("\n--- ИТОГ ---")
    print(f"Уже было готово: {len(already_ok)}")
    print(f"Переименовано сейчас: {len(renamed)}")
    print(f"Создано пустых файлов: {len(created)}")
    print(f"Пропущено вручную: {len(skipped)}")
    print(f"Ошибок: {len(errors)}")

    if errors:
        print("\nСписок ошибок:")
        for name, err in errors:
            print(f"  - {name}: {err}")

    if skipped:
        print("\nПропущенные вручную:")
        for name in skipped:
            print(f"  - {name}")


if __name__ == "__main__":
    main()

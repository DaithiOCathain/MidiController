import subprocess


def resolve_screen_number(name):
    try:
        output = subprocess.check_output(["xrandr", "--listmonitors"], text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    seen_names = []
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 4:
            continue
        index_str = parts[0].rstrip(":")
        output_name = parts[-1]
        seen_names.append(output_name)
        if output_name == name:
            try:
                return int(index_str)
            except ValueError:
                return None

    print(f"screens: '{name}' not found among {seen_names}")
    return None
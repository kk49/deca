import sys


def main():
    with open(sys.argv[1], 'r') as f:
        lines = f.readlines()

    block_count = 0
    second_block = -1
    for i, line in enumerate(lines):
        if line.startswith('####'):
            block_count += 1

        if block_count >= 2:
            second_block = i - 1
            break

    lines = lines[:second_block]
    lines = [line.replace('\n', '') for line in lines]

    while len(lines[-1]) == 0:
        lines = lines[:-1]

    for line in lines:
        print(line)


if __name__ == "__main__":
    main()

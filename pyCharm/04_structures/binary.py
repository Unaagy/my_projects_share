
def binary_search(sorted_list: list, target):
    sorted_list.sort()
    print(sorted_list)
    if len(sorted_list) == 0:
        return None

    l = 0
    r = len(sorted_list) - 1
    while l <= r:
        mid = int((r - l) / 2 + l)
        item = sorted_list[mid]
        if item == target:
            return mid
        elif item < target:
            l = mid + 1
        else:
            r = mid - 1

    return -1

items = [4, 3, 2, 8, 6, 1, 9, 5, 7, 10]
print(binary_search(items, 0))

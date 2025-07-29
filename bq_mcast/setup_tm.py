def increase_pool_size():
    print("Enlarging Queue Buffer Size")
    tm.set_app_pool_size(4, 20000000 // 80)


increase_pool_size()

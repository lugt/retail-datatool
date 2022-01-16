import csv
import json
import logging
from datetime import datetime
import xlsxwriter

filename = 'weinan5-supermarket.csv'
title_name = 'Weinan-SuperMarket'
head_found = False
titles = []
collect_info = {}

basics = ['编号', '开始答题时间', '结束答题时间', '答题时长', '地理位置国家和地区', '地理位置省', '地理位置市', '自定义字段', '1.区域名称', '2.售点名称',
          '3.售点地址', '4.运营商情况（哪家、业务办理权限等,合作级别）', '5.决策人和门店联系方式']
each_brand_info = ['手机销量', 'IoT销量', '高端机销量', '+++客户等级', '户外形象', '门头', '包柱', '第一位置', '背板', '柜台数量',
                   '体验台数量', '上柜组合', '主推政策机型', '助销礼品数量', '助销其他数量', '主力机型', '促销手段', '临促人数', '导购人数', '其他销售情况', '其他陈列和形象情况',
                   '其他情况']
special_brand_info = ['品牌名称', '手机销量', 'IoT销量', '高端机销量', '+++客户等级', '户外形象', '门头', '包柱', '第一位置', '背板', '柜台数量',
                   '体验台数量', '上柜组合', '主推政策机型', '助销礼品数量', '助销其他数量', '主力机型', '促销手段', '临促人数', '导购人数', '其他销售情况', '其他陈列和形象情况',
                   '其他情况']

multiple_choices = [{'name':'上柜达标', 'type':'brands-select', 'algo': '#'},
                    {'name':'陈列达标', 'type':'brands-select', 'algo': '#'},
                    {'name':'主推达标', 'type':'brands-select', 'algo': '#'}]

multiple_choice_brands = ['oppo', 'vivo', 'huawei', 'honor', 'xiaomi', 'apple', '都不达标']

INFO_IN_SALES_TABLE = ['编号', '名称', '地址', '运营商', '决策人', '计算店总']

algos = {
    '品牌名称': 'list', '手机销量': '+;#;c>50', 'IoT销量': '+', '高端机销量': '+',
    '+++客户等级': '+n', '户外形象': '+n', '门头': '+n;#', '包柱': '+n', '第一位置': '+n;#', '背板': '+', '柜台数量': '+',
    '体验台数量': '+', '上柜组合': 'key', '主推政策机型': 'key', '助销礼品数量': 'key;#', '助销其他数量': 'key', '主力机型': 'key',
    '促销手段': 'list', '临促人数': '+', '导购人数': '+', '其他销售情况': 'list', '其他陈列和形象情况': 'list', '其他情况': 'list'}

# '+' indicates special brand
brands = ['total', 'oppo', 'vivo', 'huawei', 'honor', 'xiaomi', 'apple', 'other']
special_brands = ['other']

other_info_in_middle = ['其他情况'] # Some info column to skip
cur_other_infos = ["其他情况",
"上柜达标:oppo",
"上柜达标:vivo",
"上柜达标:huawei",
"上柜达标:honor",
"上柜达标:xiaomi",
"上柜达标:apple",
"上柜达标:都不达标",
"陈列达标:oppo",
"陈列达标:vivo",
"陈列达标:huawei",
"陈列达标:honor",
"陈列达标:xiaomi",
"陈列达标:apple",
"陈列达标:都不达标",
"主推达标:oppo",
"主推达标:vivo",
"主推达标:huawei",
"主推达标:honor",
"主推达标:xiaomi",
"主推达标:apple",
"主推达标:都不达标"]

def as_numeric(i):
    if i is None:
        return 0
    elif i.isnumeric():
        return float(i)
    elif i.isspace():
        return 0
    elif i == '':
        return 0
    return 1


# Calculate brand info (sponge the data)
def collect_brand(brand_name, collected_info, brand_info):
    brand_infos = {}
    if collected_info.get(brand_name) is None:
        collected_info[brand_name] = brand_infos
    else:
        brand_infos = collected_info[brand_name]

    cur_offset = 0

    if brand_name in special_brands:
        current_brand_info = special_brand_info
    else:
        current_brand_info = each_brand_info

    # Gather brand info
    for item in current_brand_info:
        one_data = brand_info[cur_offset]
        cur_offset += 1
        one_algo_conts = algos[item]
        one_algo_list = one_algo_conts.split(';')
        for one_algo in one_algo_list:
            if one_algo == "+":
                assert one_data == '' or one_data.isspace() or one_data.isnumeric()
                data_as_num = as_numeric(one_data)
                name = item + '求和'
                if (brand_infos.get(name)) is None:
                    brand_infos[name] = data_as_num
                else:
                    brand_infos[name] += data_as_num
                pass
            elif one_algo.startswith("+"):  # for e.g. +n, +x
                data_num = 0
                name = item + '非零求和'
                if one_data.isnumeric():
                    data_num = float(one_data)
                elif one_data == '' or len(one_data) == 0 or one_data.isspace():
                    data_num = 0
                else:
                    data_num = 1
                    logging.info('N recognized as 1 for %, in brand %', one_data, brand_name)
                if (brand_infos.get(name)) is None:
                    brand_infos[name] = data_num
                else:
                    brand_infos[name] += data_num
                pass
            elif one_algo.startswith("#"):  # for e.g. +n, +x
                data_num = 1
                if one_data == '' or one_data.isspace() or (one_data.isnumeric() and float(one_data)) == 0:
                    data_num = 0
                name = item + '非零个数'
                if (brand_infos.get(name)) is None:
                    brand_infos[name] = data_num
                else:
                    brand_infos[name] += data_num
                pass
            elif one_algo.startswith('c>'):
                data_num = 1
                crit = float(one_algo.split('>')[1])
                if one_data == '' or one_data.isspace() or (one_data.isnumeric() and float(one_data)) < crit:
                    data_num = 0
                name = '[' + item + ']>' + str(int(crit))
                if (brand_infos.get(name)) is None:
                    brand_infos[name] = data_num
                else:
                    brand_infos[name] += data_num
                pass
            elif one_algo.startswith('key') or one_algo.startswith('list'):
                name = item + '列表'
                if one_data is not None and len(one_data) > 0:
                    if (brand_infos.get(name)) is None:
                        brand_infos[name] = [one_data]
                    else:
                        brand_infos[name].append(one_data)
                    pass
                else:
                    if (brand_infos.get(name)) is None:
                        brand_infos[name] = []
            else:
                assert False, '情况 ' + one_algo + '不可识别'
            pass     # finish if/elif
        pass # finish for

    # end of collect-brand process
    pass


def process_row(titles, row, collected_info):
    info = {}
    len_of_each_brand = len(each_brand_info)
    len_basics = len(basics)
    info['basics'] = row[0:len(basics)]
    info['name'] = row[9]
    info['location'] = row[10]
    info['sequence'] = row[0]
    info['isp'] = row[11]
    info['manager'] = row[12]
    brands_info = {}
    coloumns_processed = len_basics
    # Gather brand-specific detail info table
    for brand_name in brands:
        cur_width = len_of_each_brand
        if brand_name in special_brands:
            cur_width = len(special_brand_info)
        # The following line should be incorrect
        #brand_info = row[len_basics + brand_visited * len_of_each_brand: len_basics + (
        #            brand_visited + 1) * cur_len_of_each_brand]
        brand_info = row[coloumns_processed: coloumns_processed + cur_width]
        coloumns_processed += cur_width

        info['brand-info-' + brand_name] = brand_info

        brands_info[brand_name] = brand_info
        collect_brand(brand_name, collected_info, brand_info)

    # Get other info
    info['otherinfo'] = row[coloumns_processed]
    coloumns_processed += 1

    # Do multiple choices
    for item in multiple_choices:
        if item.get('type') == 'brands-select':
            # for each brand-select brand
            itemname = item.get('name')
            for vbrand_name in multiple_choice_brands:
                if not(vbrand_name in collected_info.keys()):
                    collected_info[vbrand_name] = {}
                brand_infos = collected_info.get(vbrand_name)
                if not (item.get('algo') == '#'):
                    raise Exception("unknown algo for multiple choice")
                # 非零个数统计
                one_data = row[coloumns_processed]
                coloumns_processed += 1
                data_num = 1
                if one_data == '' or len(one_data) == 0 or one_data.isspace() or (one_data.isnumeric() and float(one_data) == 0):
                    data_num = 0
                name = itemname + '非零个数'
                if (brand_infos.get(name)) is None:
                    brand_infos[name] = data_num
                else:
                    brand_infos[name] += data_num
                pass
        else:
            assert False, "Unknown multiple choice kind"

    info['detail'] = brands_info
    return info

# dump_as_sheets
def dump_as_sheets(workbook, outcome, origin, stores):
    cur_row_ofst = 0
    # Write headers
    for onestore in stores:
        # Create worksheet
        name = str(onestore['sequence']) + '-' + onestore['name']
        worksheet = workbook.add_worksheet(name)
        # Write basics
        basiclist = onestore['basics']
        i = 0
        base = 5
        worksheet.write_number(0, 0, as_numeric(onestore['sequence']))
        worksheet.write_string(0, 1, onestore['name'])
        worksheet.write_string(0, 7, onestore['location'])
        for item in basics:
            worksheet.write_string(1, i, item)
            worksheet.write_string(2, i, basiclist[i])
            i += 1

        brands_info = onestore['detail']
        brand_ofst = 1
        for brand_name in brands:
            brand_info = brands_info.get(brand_name)
            cur_row_ofst = 0
            pass_top = 0
            if brand_name in special_brands:
                pass_top = -1
            for item in brand_info:
                worksheet.write_string(base + pass_top + cur_row_ofst, brand_ofst, item)
                cur_row_ofst += 1
            brand_ofst += 1

        # Write titles
        cur_row_ofst = 0
        for title in each_brand_info:
            worksheet.write_string(base + cur_row_ofst, 0, title)
            cur_row_ofst += 1

        cur_row_ofst += 1
        worksheet.write_string(base + cur_row_ofst, 0, '其他情况')
        worksheet.write_string(base + cur_row_ofst, 1, onestore['otherinfo'])
        # worksheet.merge_range('B'+str(base + cur_row_ofst + 1)+':J'+str(base + cur_row_ofst + 1))

        cur_row_ofst = 0
        for brand in brands:
            worksheet.write_string(4, cur_row_ofst, brand)
            cur_row_ofst += 1

# Write to file
def write_to_file(outcome, origin, stores):
    # Create a workbook and add a worksheet.
    dt = datetime.now()
    nowstr = dt.strftime('%Y-%m-%d-%H_%M_%S')
    workbook = xlsxwriter.Workbook(title_name + '-' + nowstr + '.xlsx')
    worksheet = workbook.add_worksheet('市场竞争分析表')

    # Add a bold format to use to highlight cells.
    bold = workbook.add_format({'bold': 1})

    # Add a number format for cells with money.
    money_format = workbook.add_format({'num_format': '$#,##0'})

    # Add an Excel date format.
    date_format = workbook.add_format({'num_format': 'mmmm d yyyy'})

    # Adjust the column width.
    worksheet.set_column(1, 8, 6)

    # Write some data headers.
    # worksheet.write('A1', 'Item', bold)
    # worksheet.write('B1', 'Date', bold)
    # worksheet.write('C1', 'Cost', bold)

    # Some data we want to write to the worksheet.
    # expenses = (
    #     ['Rent', '2013-01-13', 1000],
    #     ['Gas', '2013-01-14', 100],
    #     ['Food', '2013-01-16', 300],
    #     ['Gym', '2013-01-20', 50],
    # )

    # Start from the first cell below the headers.
    row = 1
    col = 0

    # output 市场竞争分析表
    for item in brands:
        write_market_compete_info(col, item, outcome, worksheet, workbook)
        col += 1

    worksheet = workbook.add_worksheet('原始数据表')
    i = 0
    for item in basics:
        worksheet.write_string(0, i, item)
        i += 1
    for bname in brands:
        if bname in special_brands:
            cur_brand_info = special_brand_info
        else:
            cur_brand_info = each_brand_info

        for item in cur_brand_info:
            worksheet.write_string(0, i, bname + item)
            i += 1

    for item in cur_other_infos:
        worksheet.write_string(0, i, item)
        i += 1

    cur_row_ofst = 0
    for row in origin:
        j = 0
        if cur_row_ofst <= 0:
            cur_row_ofst += 1
            continue
        for entry in row:
            worksheet.write(cur_row_ofst, j, entry)
            j += 1
        cur_row_ofst += 1


    # 只有销量的表格
    dump_sales_only(workbook, stores)

    # 导出销量扩展表
    dump_sales_extended(workbook, stores)

    # Dump 售点档案表
    dump_as_sheets(workbook, outcome, origin, stores)


    workbook.close()


def dump_sales_only(workbook, stores):
    worksheet = workbook.add_worksheet('销量统计表')
    # Title1 Title2 ....
    # Seq
    row = 1
    infos = INFO_IN_SALES_TABLE

    col = 0
    for item in infos:
        worksheet.write_string(0, col, item)
        col += 1

    for item in brands:
        worksheet.write_string(0, col, item)
        col += 1

    for store in stores:
        dump_basics(worksheet, store, row)
        base = 6
        i = 0
        for brand in brands:
            if brand == 'other':
                brand_sales = as_numeric(store['detail'].get(brand)[1])
            else:
                brand_sales = as_numeric(store['detail'].get(brand)[0])
            worksheet.write_number(row, base + i, brand_sales)
            i += 1
            pass
        row += 1
        pass


def dump_basics(worksheet, store, row):
    brands_total = 0
    for brand in brands:
        if brand == 'total':
            continue

        brand_sales = as_numeric(store['detail'].get(brand)[0])
        brands_total += brand_sales

    # Add other products into count
    brands_total += as_numeric(store['detail'].get('other')[1])

    worksheet.write_number(row, 0, as_numeric(store['sequence']))
    worksheet.write_string(row, 1, store['name'])
    worksheet.write_string(row, 2, store['location'])
    worksheet.write_string(row, 3, store['isp'])
    worksheet.write_string(row, 4, store['manager'])
    worksheet.write_number(row, 5, brands_total)


def dump_sales_extended(workbook, stores):
    worksheet = workbook.add_worksheet('销售扩展表')
    # Title1 Title2 ....
    # Seq
    row = 1
    infos = INFO_IN_SALES_TABLE

    col = 0
    for item in infos:
        worksheet.write_string(0, col, item)
        col += 1

    for item in brands:
        worksheet.write_string(0, col, item + '销量')
        col += 1
        worksheet.write_string(0, col, item + '导购')
        col += 1

    for store in stores:
        dump_basics(worksheet, store, row)
        base = 6
        i = 0
        for brand in brands:
            extra = 0
            if brand == 'other':
                extra = 1
            # 销量
            brand_sales = as_numeric(store['detail'].get(brand)[extra + 0])
            worksheet.write_number(row, base + i, brand_sales)
            i += 1
            # 导购人数
            brand_sellers = as_numeric(store['detail'].get(brand)[extra + 18])
            worksheet.write_number(row, base + i, brand_sellers)
            i += 1
            pass

        # end of row
        row += 1
        pass


def write_cell_vertical(col, cur_row, worksheet, data, type='n'):
    if type == 'n':
        worksheet.write_number(cur_row, col, float(data))
    elif type == 'l':
        worksheet.write_string(cur_row, col, str(data))
    else:
        worksheet.write_string(cur_row, col, data)
    return cur_row + 1


def zero_div(x, y):
    if x == 0 or (x == 0 and y == 0) or y == 0:
        return 0
    else:
        return x / y

def get_or_zero(obj, name):
    if (obj.get(name) is None):
        return 0
    else:
        return obj.get(name)


def write_market_compete_info(col, brand_name, outcome, worksheet, workbook, start_row=0):

    # Convert the date string into a datetime object.
    # date = datetime.strptime(date_str, "%Y-%m-%d")
    #
    # worksheet.write_string(row, col, item)
    # worksheet.write_datetime(row, col + 1, date, date_format)
    # worksheet.write_number(row, col + 2, cost, money_format)
    # row += 1
    cur_row = 0
    assert (outcome.get(brand_name) is not None), 'brand not found ' + brand_name
    curbrand = outcome[brand_name]
    aggregates = outcome['aggregates']
    # 销量
    # ['手机销量', 'IoT销量', '高端机销量', '+++客户等级', '户外形象', '门头', '包柱', '第一位置', '背板', '柜台数量',
    # '体验台数量', '上柜组合', '主推政策机型', '助销礼品数量', '助销其他数量', '主力机型', '促销手段', '临促人数',
    # '导购人数', '其他销售情况', '其他陈列和形象情况',
    # '其他情况']
    cur_row = write_cell_vertical(col, cur_row, worksheet, curbrand['手机销量求和'])
    # 市场占有率
    cur_row = write_cell_vertical(col, cur_row, worksheet, zero_div(curbrand['手机销量求和'], aggregates['market_size']))
    # 分销
    cur_row = write_cell_vertical(col, cur_row, worksheet, curbrand['手机销量非零个数'])
    # 分销率
    cur_row = write_cell_vertical(col, cur_row, worksheet, zero_div(curbrand['手机销量非零个数'] , aggregates['store_count']))
    # 单店销量
    cur_row = write_cell_vertical(col, cur_row, worksheet, zero_div(curbrand['手机销量求和'] , curbrand['手机销量非零个数']))
    # 门头投放
    cur_row = write_cell_vertical(col, cur_row, worksheet, curbrand['门头非零求和'])
    # 门柱投放
    # cur_row = write_cell_vertical(col, cur_row, worksheet, curbrand['包柱非零求和'])
    # 背板投放
    cur_row = write_cell_vertical(col, cur_row, worksheet, curbrand['背板求和'])
    # 柜台投放
    cur_row = write_cell_vertical(col, cur_row, worksheet, curbrand['柜台数量求和'] + curbrand['体验台数量求和'])
    # 上柜达标率 TODO: fixup
    cur_row = write_cell_vertical(col, cur_row, worksheet, zero_div(get_or_zero(curbrand, '上柜达标非零个数'), curbrand['手机销量非零个数']))
    # 主推达标率 TODO: fixup
    cur_row = write_cell_vertical(col, cur_row, worksheet, zero_div(get_or_zero(curbrand, '主推达标非零个数'), curbrand['手机销量非零个数']))
    # 陈列达标率 TODO: fixup
    cur_row = write_cell_vertical(col, cur_row, worksheet, zero_div(get_or_zero(curbrand, '陈列达标非零个数'), curbrand['手机销量非零个数']))
    # 助销达标率
    cur_row = write_cell_vertical(col, cur_row, worksheet, zero_div(curbrand['助销礼品数量非零个数'], curbrand['手机销量非零个数']))
    # 核心售点数
    cur_row = write_cell_vertical(col, cur_row, worksheet, curbrand['[手机销量]>50'])
    # 主力机型 / 价格
    cur_row = write_cell_vertical(col, cur_row, worksheet, curbrand['主力机型列表'], type='l')
    # 促销手段
    cur_row = write_cell_vertical(col, cur_row, worksheet, curbrand['促销手段列表'], type='l')
    # 促销员人数
    cur_row = write_cell_vertical(col, cur_row, worksheet, curbrand['导购人数求和'])

    # Write a total using a formula.
    # worksheet.write(row, 0, 'Total', bold)
    # worksheet.write(row, 2, '=SUM(C2:C5)', money_format)
    pass


def aggregate_stores(onepass, origin, stores):
    # Calculate total stores
    out = {}
    out['store_count'] = len(stores)
    total_valids = 0
    total_sales = 0
    for store in stores:
        brands_total = 0
        for brand in brands:
            if brand == 'total':
                continue
            brand_sales = as_numeric(store['detail'].get(brand)[0])
            brands_total += brand_sales
        if brands_total > 0:
            total_valids += 1
        total_sales += brands_total
    # Determine sales of each store, then the recalculate total-sales
    out['market_size'] = total_sales
    onepass['total']['手机销量求和'] = total_sales
    onepass['total']['手机销量非零个数'] = len(stores)
    # fix 手机销量求和 for all brands
    onepass['aggregates'] = out
    pass

if __name__ == '__main__':
    aggregates = {}
    origin = []
    stores = []
    with open(filename, newline='', encoding='utf8') as csvf:
        reader = csv.reader(csvf)
        for row in reader:
            origin.append(row)
            if not head_found:
                titles = row
                # TODO: verify titles are correct.
            else:
                # Real data.
                one_store = process_row(titles, row, aggregates)
                stores.append(one_store)

            head_found = True
            print(row)

    aggregate_stores(aggregates, origin, stores)

    print(json.dumps(aggregates, indent=1))
    print(aggregates)
    write_to_file(aggregates, origin, stores)

titles_example = ['编号', '开始答题时间', '结束答题时间', '答题时长', '地理位置国家和地区', '地理位置省', '地理位置市', '自定义字段', '1.区域名称', '2.售点名称',
                  '3.售点地址', '4.运营商情况（哪家、业务办理权限等,合作级别）', '5.决策人和门店联系方式',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, '
                  '第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,'
                  '助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,'
                  '其他销售情况_________,其他陈列和形象情况_________,其他情况_________:1[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, '
                  '第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,'
                  '助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,'
                  '其他销售情况_________,其他陈列和形象情况_________,其他情况_________:2[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:3[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:4[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:5[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:6[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:7[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:8[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:9[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:10[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:11[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:12[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:13[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:14[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:15[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:16[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:17[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:18[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:19[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:20[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:21[题目填空]',
                  '6.题目: 全店铺手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:22[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:1[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:2[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:3[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:4[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:5[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:6[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:7[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:8[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:9[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:10[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:11[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:12[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:13[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:14[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:15[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:16[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:17[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:18[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:19[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:20[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:21[题目填空]',
                  '7.题目: OPPO手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:22[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:1[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:2[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:3[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:4[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:5[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:6[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:7[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:8[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:9[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:10[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:11[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:12[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:13[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:14[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:15[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:16[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:17[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:18[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:19[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:20[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:21[题目填空]',
                  '8.题目: vivo手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:22[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:1[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:2[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:3[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:4[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:5[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:6[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:7[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:8[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:9[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:10[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:11[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:12[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:13[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:14[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:15[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:16[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:17[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:18[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:19[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:20[题目填空]',
                  '9.题目: 华为手机销量_______,IoT销量_______,高端机销量_______,客户登记_______,户外形象_______,门头_______,包柱________, 第一位置_________,背板_________,柜台数量_________,体验台数量_________,上柜组合_________,主推政策机型_________,助销礼品数量_________,助销其他数量_________,主力机型_________,促销手段_________,临促人数_________,导购人数_________,其他销售情况_________,其他陈列和形象情况_________,其他情况_________:21[题目填空]']

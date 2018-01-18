import os
import json
import xlwt, xlrd
import logging
import zipfile
import shutil
import mimetypes

from io import StringIO, BytesIO
from datetime import datetime
from django.http import HttpResponseRedirect, HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from wsgiref.util import FileWrapper

logger_info = logging.getLogger('wms.wms_app.func_utils_info')
logger_error = logging.getLogger('wms.wms_app.func_utils_error')

#excel单元格最长字符长度32767
MAX_EXCEL_DATA = 32767

#ajax最大连接数
MAX_AJAX_LINK = 5

#当前ajax连接数
ajax_reqs = 0

#GBK编码文件列表
GBK_FILE_LIST = ['autoTest_console_logcat.txt', 'autoTest_javaLayer_crash.txt', 'autoTest_logcat.txt', 'install_logcat.txt',
    'taskinfo']

#从excel中读取form数据
def read_excel(request):
    excel_dir = settings.BASE_DIR + '/output/' + get_fileserver_base_dir(request) + '/result.xlsx'
    table_data = []
    if os.path.isfile(excel_dir):
        data = xlrd.open_workbook(excel_dir)
        table = data.sheets()[0]
        nrows = table.nrows
        for i in range(1, nrows):
            mobile = table.row_values(i)[0]
            resolution = table.row_values(i)[1]
            sdk = table.row_values(i)[2]
            data = table.row_values(i)[3]
            table_d = {}
            table_d = {
                'mobile': mobile,
                'resolution': resolution,
                'sdk': sdk,
                'data': data
            }
            table_data.append(table_d)
    return table_data

#分发ajax请求
def dif_modal(request):
    modal_name = request.POST.get('modal_name')
    if modal_name == 'selectLog':
        return select_log(request)
    elif modal_name == 'avoidTimeout':
        return avoid_timeout(request)

#获取文件大小
def get_file_size(filePath):
    # filePath = unicode(filePath,'utf8')
    fsize = os.path.getsize(filePath)
    fsize = fsize/float(1024*1024)
    return round(fsize, 2)

#获取log路径
def get_fileserver_base_dir(request):
    job_id = request.GET.get('job_id')
    begin_time = request.GET.get('begin_time')
    log_time = begin_time.split(' ')[0].replace('-','')
    fileserver_base_dir = log_time + '/' + job_id
    return fileserver_base_dir

#递归删除文件夹下的所有文件，p参数包括本文件夹，默认删除本文件夹
def del_dir(path, p=True):
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    if p:
        os.rmdir(path)

#递归创建文件夹
def make_dir_p(path):
    if not os.path.isdir(path):
        os.makedirs(path)

#直接读取压缩包写要提取的文件，无需解压缩操作
def write_file_zip(zfile, dst_log_name, dst_path, mobile_name, file_or_dir):
    try:
        for file in zfile.namelist():
            if file.endswith('.zip'):
                tzfile = zipfile.ZipFile(BytesIO(zfile.read(file)))
                write_file_zip(tzfile, dst_log_name, dst_path, mobile_name, file_or_dir)
            elif dst_log_name in file:
                if file_or_dir == 'file':
                    file_name = file[file.rfind('/')+1:]
                    with zfile.open(file, 'r') as f:
                        with open(dst_path + mobile_name + '_' + file_name, 'wb') as temp:
                            temp.write(f.read())
                            temp.seek(0)
                elif file_or_dir == 'dir':
                    if not file.endswith('/'):
                        file_path = dst_path + mobile_name + '_' + file[file.find(dst_log_name):file.rfind('/')] + '/'
                        file_name = file[file.rfind('/')+1:]
                        make_dir_p(file_path)
                        with zfile.open(file, 'r') as f:
                            with open(file_path + file_name, 'wb') as temp:
                                temp.write(f.read())
                                temp.seek(0)
    except Exception as e:
        logger_error.error('-write_file_zip fail!---' + str(e) + '---' + file_name)
    finally:
        zfile.close()

#直接读压缩包中的Log.txt数据，无需解压缩
def get_sdk_zip(zfile, file_name):
    try:
        for file in zfile.namelist():
            if file.endswith('.zip'):
                tzfile = zipfile.ZipFile(BytesIO(zfile.read(file)))
                return get_sdk_zip(tzfile, file_name)
            elif file_name in file:
                with zfile.open(file, 'r') as f:
                    for line in f.readlines():
                        line = line.decode('utf-8').strip()
                        if line.count('|') > 2:
                            sdk = line.split('|')[2].strip()
                            return sdk
    except Exception as e:
        logger_error.error('-get_sdk_zip fail!---' + str(e) + '---' + file_name)
    finally:
        zfile.close()

#直接读压缩包中的关键内容数据，无需解压缩
def get_data_zip(zfile, key_log_name, key_name):
    data = []
    try:
        for file in zfile.namelist():
            if file.endswith('.zip'):
                tzfile = zipfile.ZipFile(BytesIO(zfile.read(file)))
                return get_data_zip(tzfile, key_log_name, key_name)
            elif key_log_name in file:
                with zfile.open(file, 'r') as f:
                    for line in f.readlines():
                        if key_log_name in GBK_FILE_LIST:
                            line = line.decode('GBK').strip()
                            if key_name in line:
                                data.append(line)
                        else:
                            line = line.decode('utf-8').strip()
                            if key_name in line:
                                data.append(line)
                    return '\n'.join(data)
    except Exception as e:
        logger_error.error('-get_data_zip fail!---' + str(e) + '---' + file_name)
    finally:
        zfile.close()

#生成excel
def write_excel(res_data, not_res_data, output_path):
    row_res = len(res_data)
    row_not_res = len(not_res_data)
    style_heading = xlwt.easyxf("""
    font:
        name Arial,
        colour_index white,
        bold on,
        height 0xA0;
    align:
        wrap off,
        vert center,
        horiz center;
    pattern:
        pattern solid,
        fore-colour 0x19;
    borders:
        left THIN,
        right THIN,
        top THIN,
        bottom THIN;
    """)
    wb = xlwt.Workbook(encoding='utf-8')
    sheet_res = wb.add_sheet('key_res')
    sheet_res.write(0, 0, '机型', style_heading)
    sheet_res.write(0, 1, '分辨率', style_heading)
    sheet_res.write(0, 2, 'SDK', style_heading)
    sheet_res.write(0, 3, '数据', style_heading)
    for row in range(row_res):
        sheet_res.write(row+1, 0, res_data[row]['mobile_name'])
        sheet_res.write(row+1, 1, res_data[row]['resolution'])
        sheet_res.write(row+1, 2, res_data[row]['sdk'])
        sheet_res.write(row+1, 3, res_data[row]['data'])
    sheet_not_res = wb.add_sheet('not_key_res')
    sheet_not_res.write(0, 0, '机型', style_heading)
    sheet_not_res.write(0, 1, '分辨率', style_heading)
    sheet_not_res.write(0, 2, 'SDK', style_heading)
    sheet_not_res.write(0, 3, '数据', style_heading)
    for row in range(row_not_res):
        sheet_not_res.write(row+1, 0, not_res_data[row]['mobile_name'])
        sheet_not_res.write(row+1, 1, not_res_data[row]['resolution'])
        sheet_not_res.write(row+1, 2, not_res_data[row]['sdk'])
        sheet_not_res.write(row+1, 3, not_res_data[row]['data'])
    wb.save(output_path + '/result.xlsx')

#以zip为结尾的LOG列表
def zip_files(path, output_path):
    zip_files_list = []
    try:
        zip_files_list = [file_name for file_name in os.listdir(path) if file_name.endswith('.zip')]
    except FileNotFoundError as e:
        logger_error.error('-source log fail!---' + str(e))
        del_dir(output_path, False)
    return zip_files_list

#LOG筛选准备
def init_select_log(output_path, key_res_path, not_key_res_path):
    #创建目录
    del_dir(output_path, False)
    make_dir_p(key_res_path)
    make_dir_p(not_key_res_path)

#LOG筛选之后清理
def clean_select_log(key_res_path, not_key_res_path):
    #删除临时目录
    del_dir(key_res_path)
    del_dir(not_key_res_path)

#跳板机超时，自动刷新页面结果防止页面一直不刷新
def avoid_timeout(request):
    res_dir_list = os.listdir(settings.BASE_DIR + '/output/' + get_fileserver_base_dir(request) +'/')
    if 'not_key_res' in res_dir_list:
        return HttpResponse(json.dumps({'status':'fail'}))
    else:
        return HttpResponse(json.dumps({'status':'success'}))

#筛选log主函数
def select_log(request):
    global ajax_reqs
    logger_info.info("-ajax_reqs:" + str(ajax_reqs))
    if ajax_reqs >= MAX_AJAX_LINK:
        return HttpResponse(json.dumps({'status':'ajax_reach_max_link'}))
    ajax_reqs = ajax_reqs + 1

    key_log_name = request.POST.get('key_log_name')
    key_name = request.POST.get('key_name')
    dst_log_name = request.POST.get('dst_log_name')
    file_or_dir = request.POST.get('file_or_dir')
    key_name_list = key_name.split(',')
    dst_log_name_list = dst_log_name.split(',')
    res_data = []
    not_res_data = []
    path = '/data/fileserver/' + get_fileserver_base_dir(request) + '/'
    # test dir (windows os)
    #path = 'F:/work/other_project/teddy/read_result/logcat/'
    output_base_path = settings.BASE_DIR + '/output/'
    output_path = output_base_path + get_fileserver_base_dir(request) +'/'
    key_res_path = output_base_path + get_fileserver_base_dir(request) +'/key_res/'
    not_key_res_path = output_base_path + get_fileserver_base_dir(request) +'/not_key_res/'
    
    init_select_log(output_path, key_res_path, not_key_res_path)

    #log中记录参数
    logger_info.info("-key_log_name:" + key_log_name + ' ---key_name:' + key_name + ' ---dst_log_name:'+ dst_log_name + 
        ' ---file_or_dir:' + file_or_dir)

    #后门-删除后台所有LOG
    if key_log_name == '*******' and key_name == '*******' and dst_log_name == '*******':
        del_dir(output_path, False)
        ajax_reqs = ajax_reqs - 1
        return HttpResponse(json.dumps({'status':'success'}))

    #关键字所在文件名为空  且  提取目标为空，或者，关键字所在文件名不为空  且  关键字为空且提取目标为空  ——  所有机型所有LOG
    elif (not key_log_name and not dst_log_name) or (key_log_name and not key_name and not dst_log_name):
        log_files = zip_files(path, output_path)
        if log_files:
            for file_name in log_files:
                #shutil.copy(path + file_name, key_res_path)
                os.system('cp "' + path + file_name + '" ' + key_res_path)
            #shutil.make_archive(output_path + 'key_res', 'zip', key_res_path)
            os.system('zip -r -qj ' + output_path + 'key_res.zip ' + key_res_path)
        else:
            ajax_reqs = ajax_reqs - 1
            return HttpResponse(json.dumps({'status':'source_log_fail'}))

    #关键字所在文件名为空  且  提取目标不为空，或者，关键字所在文件名不为空  且  关键字为空且提取目标不为空  ——  所有机型指定LOG
    elif (not key_log_name and dst_log_name) or (key_log_name and not key_name and dst_log_name):
        log_files = zip_files(path, output_path)
        if log_files:
            for file_name in log_files:
                mobile_name = file_name.split('_')[1] + '_' + file_name.split('_')[2]
                for dst_log_name in dst_log_name_list:
                    zfile = zipfile.ZipFile(path + file_name)
                    write_file_zip(zfile, dst_log_name, key_res_path, mobile_name, file_or_dir)
            #shutil.make_archive(output_path + 'key_res', 'zip', key_res_path)
            os.system('zip -r -qj ' + output_path + 'key_res.zip ' + key_res_path)
        else:
            ajax_reqs = ajax_reqs - 1
            return HttpResponse(json.dumps({'status':'source_log_fail'}))

    #关键字所在文件名不为空  且  关键字不为空  且  提取目标为空  ——  包含关键内容机型的所有LOG
    elif (key_log_name and key_name and not dst_log_name):
        log_files = zip_files(path, output_path)
        if log_files:
            for file_name in log_files:
                try:
                    mobile_name = file_name.split('_')[1] + '_' + file_name.split('_')[2]
                    resolution = file_name.split('_')[3]

                    zfile = zipfile.ZipFile(path + file_name)
                    sdk = get_sdk_zip(zfile, 'Log.txt')
                    if not sdk:
                        sdk = ''
                    data = []
                    for key_name in key_name_list:
                        zfile = zipfile.ZipFile(path + file_name)
                        zdata = get_data_zip(zfile, key_log_name, key_name)
                        if not zdata:
                            zdata = ''
                        data.append(zdata)
                    data = ('\n'.join(data)).strip()
                    
                    #处理excel超过32767字符异常
                    if len(data) > MAX_EXCEL_DATA:
                        del_dir(output_path, False)
                        ajax_reqs = ajax_reqs - 1
                        return HttpResponse(json.dumps({'status':'large_data_fail'}))

                    if not data:
                        try:
                            #shutil.copy(path + file_name, not_key_res_path)
                            os.system('cp "' + path + file_name + '" ' + not_key_res_path)
                        except Exception as e:
                            logger_error.error('-move not key file fail!---' + str(e) + '---' + file_name)

                        nr = {}
                        nr = {
                            'mobile_name': mobile_name,
                            'resolution': resolution,
                            'sdk': sdk,
                            'data': data
                        }
                        not_res_data.append(nr)
                    else:
                        try:
                            #shutil.copy(path + file_name, key_res_path)
                            os.system('cp "' + path + file_name + '" ' + key_res_path)
                        except Exception as e:
                            logger_error.error('-move key file fail!---' + str(e) + '---' + file_name)

                        r = {}
                        r = {
                            'mobile_name': mobile_name,
                            'resolution': resolution,
                            'sdk': sdk,
                            'data': data
                        }
                        res_data.append(r)
                except Exception as e:
                    logger_error.error('-find file fail!---' + str(e) + '---' + file_name)
                    nr = {}
                    nr = {
                        'mobile_name': mobile_name,
                        'resolution': resolution,
                        'sdk': sdk,
                        'data': data
                    }
                    not_res_data.append(nr)
            write_excel(res_data, not_res_data, output_path)

            #shutil.make_archive(output_path + 'key_res', 'zip', key_res_path)
            os.system('zip -r -qj ' + output_path + 'key_res.zip ' + key_res_path)
            #shutil.make_archive(output_path + 'not_key_res', 'zip', not_key_res_path)
            os.system('zip -r -qj ' + output_path + 'not_key_res.zip ' + not_key_res_path)
        else:
            ajax_reqs = ajax_reqs - 1
            return HttpResponse(json.dumps({'status':'source_log_fail'}))

    #关键字所在文件名不为空  且  关键字不为空  且  提取目标不为空  ——  包含关键内容机型的指定LOG
    elif (key_log_name and key_name and dst_log_name):
        log_files = zip_files(path, output_path)
        if log_files:
            for file_name in log_files:
                try:
                    mobile_name = file_name.split('_')[1] + '_' + file_name.split('_')[2]
                    resolution = file_name.split('_')[3]

                    zfile = zipfile.ZipFile(path + file_name)
                    sdk = get_sdk_zip(zfile, 'Log.txt')
                    if not sdk:
                        sdk = ''
                    data = []
                    for key_name in key_name_list:
                        zfile = zipfile.ZipFile(path + file_name)
                        zdata = get_data_zip(zfile, key_log_name, key_name)
                        if not zdata:
                            zdata = ''
                        data.append(zdata)
                    data = ('\n'.join(data)).strip()
                    
                    #处理excel超过32767字符异常
                    if len(data) > MAX_EXCEL_DATA:
                        del_dir(output_path, False)
                        ajax_reqs = ajax_reqs - 1
                        return HttpResponse(json.dumps({'status':'large_data_fail'}))

                    if not data:
                        for dst_log_name in dst_log_name_list:
                            zfile = zipfile.ZipFile(path + file_name)
                            write_file_zip(zfile, dst_log_name, not_key_res_path, mobile_name, file_or_dir)

                        nr = {}
                        nr = {
                            'mobile_name': mobile_name,
                            'resolution': resolution,
                            'sdk': sdk,
                            'data': data
                        }
                        not_res_data.append(nr)
                    else:
                        for dst_log_name in dst_log_name_list:
                            zfile = zipfile.ZipFile(path + file_name)
                            write_file_zip(zfile, dst_log_name, key_res_path, mobile_name, file_or_dir)

                        r = {}
                        r = {
                            'mobile_name': mobile_name,
                            'resolution': resolution,
                            'sdk': sdk,
                            'data': data
                        }
                        res_data.append(r)
                except Exception as e:
                    logger_error.error('-find file fail!---' + str(e) + '---' + file_name)
                    nr = {}
                    nr = {
                        'mobile_name': mobile_name,
                        'resolution': resolution,
                        'sdk': sdk,
                        'data': data
                    }
                    not_res_data.append(nr)
            write_excel(res_data, not_res_data, output_path)

            #shutil.make_archive(output_path + 'key_res', 'zip', key_res_path)
            os.system('zip -r -qj ' + output_path + 'key_res.zip ' + key_res_path)
            #shutil.make_archive(output_path + 'not_key_res', 'zip', not_key_res_path)
            os.system('zip -r -qj ' + output_path + 'not_key_res.zip ' + not_key_res_path)
        else:
            ajax_reqs = ajax_reqs - 1
            return HttpResponse(json.dumps({'status':'source_log_fail'}))
    
    clean_select_log(key_res_path, not_key_res_path)
    ajax_reqs = ajax_reqs - 1
    return HttpResponse(json.dumps({'status':'success'}))

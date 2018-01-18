import os
import logging
import zipfile
import mimetypes

from datetime import datetime
from datetime import timedelta
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseRedirect, HttpResponse, StreamingHttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from wsgiref.util import FileWrapper
from .func_utils import dif_modal, read_excel, get_fileserver_base_dir, get_file_size

logger_info = logging.getLogger('wms.wms_app.views_info')
logger_error = logging.getLogger('wms.wms_app.views_error')

@csrf_exempt
def dat_log_analysis(request):
    if request.is_ajax():
        logger_info.info('-url:' + request.get_full_path() + '---ajax_request---' + request.POST.get('modal_name'))
        return dif_modal(request)
    else:
        logger_info.info('-url:' + request.get_full_path() + '---get_request')
        job_id = request.GET.get('job_id')
        begin_time = request.GET.get('begin_time')
        log_time = begin_time.split(' ')[0].replace('-','')
        
        contain_key_log = ''
        not_contain_key_log = ''
        log_excel = ''
        zip_dir = settings.BASE_DIR + '/output/' + get_fileserver_base_dir(request)
        if os.path.isfile(zip_dir + '/key_res.zip'):
            size = get_file_size(zip_dir + '/key_res.zip')
            contain_key_log = '包含关键字信息的日志.zip('+ str(size) + 'M)'
        if os.path.isfile(zip_dir + '/not_key_res.zip'):
            size = get_file_size(zip_dir + '/not_key_res.zip')
            not_contain_key_log = '不包含关键字信息的日志.zip('+ str(size) + 'M)'
        if os.path.isfile(zip_dir + '/result.xlsx'):
            size = get_file_size(zip_dir + '/result.xlsx')
            log_excel = '机型数据列表.xlsx('+ str(size) + 'M)'
        table_data = read_excel(request)
        return render(request, 'dat_log_analysis.html', {'contain_key_log':contain_key_log, 'not_contain_key_log':not_contain_key_log, 
            'log_excel':log_excel , 'table_data':table_data, 'job_id':job_id, 'begin_time':begin_time})

@csrf_exempt
def download_log(request):
    logger_info.info('-url:' + request.get_full_path())
    filename = request.GET.get('filename')
    if filename == 'key_res':
        filepath = settings.BASE_DIR + '/output/' + get_fileserver_base_dir(request) + '/key_res.zip'
        log_name = 'key_res.zip'
    elif filename == 'not_key_res':
        filepath = settings.BASE_DIR + '/output/' + get_fileserver_base_dir(request) + '/not_key_res.zip'
        log_name = 'not_key_res.zip'
    elif filename == 'result':
        filepath = settings.BASE_DIR + '/output/' + get_fileserver_base_dir(request) + '/result.xlsx'
        log_name = 'result.xlsx'

    wrapper = FileWrapper(open(filepath, 'rb'))
    content_type = mimetypes.guess_type(filepath)[0]
    response = StreamingHttpResponse(wrapper, 'content_type')
    response['Content-Disposition'] = 'attachment; filename=' + log_name
    return response
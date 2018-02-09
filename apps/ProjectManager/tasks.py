# -*- coding:utf-8 -*-
# edit by fuzongfei

from AuditSQL.settings import EMAIL_FROM
from celery import shared_task
from django.core.mail import EmailMessage
from django.db.models import F
from django.template.loader import render_to_string

from ProjectManager.models import OnlineAuditContents
from UserManager.models import ContactsDetail, UserAccount, Contacts


class GetUserInfo(object):
    def __init__(self, latest_id):
        self.latest_id = latest_id

    def get_user_email(self):
        obj = OnlineAuditContents.objects.get(id=self.latest_id)
        user_list = [obj.proposer, obj.verifier, obj.operate_dba]
        user_email = list(UserAccount.objects.filter(username__in=user_list).values_list('email', flat=True))
        return user_email

    def get_contact_email(self):
        cc = list(OnlineAuditContents.objects.get(pk=self.latest_id).email_cc.split(','))
        contact_email = list(Contacts.objects.filter(contact_id__in=cc).values_list('contact_email', flat=True))
        return contact_email

    # 获取项目组密送成员的邮箱
    def get_bcc_email(self):
        group_id = OnlineAuditContents.objects.get(pk=self.latest_id).group_id
        bcc_email = ContactsDetail.objects.filter(group__group_id=group_id).filter(bcc='1').annotate(
            contact_email=F('contact__contact_email')
        ).values_list('contact_email', flat=True)
        return list(bcc_email)


@shared_task
def send_commit_mail(**kwargs):
    latest_id = kwargs['latest_id']
    userinfo = GetUserInfo(latest_id)

    receiver = userinfo.get_user_email()
    cc = userinfo.get_contact_email()
    bcc = userinfo.get_bcc_email()

    # 向_commit_mail.html渲染data数据
    record = OnlineAuditContents.objects.annotate(group_name=F('group__group_name')).get(pk=latest_id)
    email_html_body = render_to_string('_send_commit_mail.html', {'data': record})

    # 发送邮件
    msg = EmailMessage(subject=record.title,
                       body=email_html_body,
                       from_email=EMAIL_FROM,
                       to=receiver,
                       cc=cc,
                       bcc=bcc,
                       )
    msg.content_subtype = "html"

    # 如果存在上传文件，作为附件发送
    # attachments = UploadFiles.objects.filter(content_id=latest_id).filter(type='0')
    # if attachments:
    #     for i in attachments:
    #         msg.attach_file(r'media/{}'.format(i.files))
    msg.send()


# @shared_task
# def send_verify_mail(**kwargs):
#     latest_id = kwargs['latest_id']
#     proposer = get_user_email(latest_id, 'proposer')
#     leader = get_user_email(latest_id, 'verifier')
#     dba = get_user_email(latest_id, 'operate_dba')
#     mail_cc = get_contact_email(latest_id)
#     bcc = get_bcc_email(latest_id)
#
#     # 收件人, 为申请人、dba、leader
#     mail_receiver = list(set(proposer + dba + leader))
#
#     # 抄送人，为leader和申请人
#     mail_cc = mail_cc
#
#     # 向mail_template.html渲染data数据
#     record = AuditContents.objects.get(pk=latest_id)
#     detail = AuditContentsDetail.objects.get(content_id=latest_id)
#     email_html_body = render_to_string('_audits_verify_mail.html', {
#         'data': record,
#         'detail': detail,
#         'user_role': kwargs['user_role'],
#         'username': kwargs['username']
#     })
#
#     # 发送邮件
#     headers = {'Reply: ': mail_receiver}
#     title = 'Re: ' + record.title
#     msg = EmailMessage(subject=title,
#                        body=email_html_body,
#                        from_email=EMAIL_FROM,
#                        to=mail_receiver,
#                        cc=mail_cc,
#                        bcc=bcc,
#                        headers=headers)
#     msg.content_subtype = "html"
#     msg.send()
#
# @shared_task
# def send_reply_mail(**kwargs):
#     latest_id = kwargs['latest_id']
#     reply_id = kwargs['reply_id']
#     proposer = get_user_email(reply_id, 'proposer')
#     leader = get_user_email(reply_id, 'verifier')
#     dba = get_user_email(reply_id, 'operate_dba')
#     mail_cc = get_contact_email(reply_id)
#     bcc = get_bcc_email(latest_id)
#
#     # 收件人, 为申请人、dba、leader
#     mail_receiver = list(set(proposer + dba + leader))
#
#     # 抄送人，为leader和申请人
#     mail_cc.append(kwargs['email'])
#
#     title = AuditContents.objects.get(pk=reply_id).title
#     reply_record = AuditContentsReply.objects.get(pk=latest_id)
#
#     # 向mail_template.html渲染data数据
#     email_html_body = render_to_string('_audits_reply_mail.html', {
#         'reply_record': reply_record,
#         'username': kwargs['username'],
#     })
#
#     # 发送邮件
#     headers = {'Reply: ': mail_cc}
#     title = 'Re: ' + title
#     msg = EmailMessage(subject=title,
#                        body=email_html_body,
#                        from_email=EMAIL_FROM,
#                        to=mail_receiver,
#                        cc=mail_cc,
#                        bcc=bcc,
#                        headers=headers)
#     msg.content_subtype = "html"
#     msg.send()
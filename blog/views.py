# -*- coding: utf-8 -*-

from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Comment
from .forms import EmailPostForm, CommentForm, SearchForm

from django.core.paginator import Paginator, EmptyPage,\
    PageNotAnInteger

from django.views.generic import ListView
from django.core.mail import send_mail

from django.contrib import messages
from django.core.urlresolvers import reverse

from taggit.models import Tag

from haystack.query import SearchQuerySet

# class PostListView(ListView):
#     queryset = Post.published.all()
#     context_object_name = 'posts'
#     paginate_by = 2
#     template_name = 'blog/post/list.html'

def post_list(request, tag_slug=None):
    object_list = Post.published.all()
    tag = None

    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])

    paginator = Paginator(object_list, 30) # 30 posts in each page
    page = request.GET.get('page')

    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer deliver the first page
        posts = paginator.page(1)
    except EmptyPage:
        # If page is out of range deliver last page of results
        posts = paginator.page(paginator.num_pages)

    return render(request,
                  'blog/post/list.html',
                  {'posts': posts,
                   'tag': tag})


def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post, slug=post,
                             status='published',
                             publish__year=year,
                             publish__month=month,
                             publish__day=day)

    comments = post.comments.filter(active=True)
    if request.method == 'POST':
        # wrong decision to create comments within post controller !!!!
        comment_form = CommentForm(data=request.POST) # interesting idea: create comment from form , not from model
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post
            new_comment.save()

            # ! в отличие от книги, я использую флеш-сообщения, а не отображаю сообщение "всё отправлено" в template
            messages.add_message(
                request,
                messages.SUCCESS,
                'Comment added!')

            # поэтому я редирекчу
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    else:
        comment_form = CommentForm()


    return render(request,
                  'blog/post/detail.html',
                  {'post': post,
                  'comments': comments,
                  'comment_form': comment_form})


def post_share(request, post_id):
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False
    if request.method == 'POST':
        form = EmailPostForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject  = '{} ({}) recommends you reading "{}"'\
                .format(cd['name'], cd['email'], post.title)
            message = 'Read "{}" at {}\n\n{}\'s comments: {}'\
                .format(post.title, post_url, cd['name'], cd['comments'])
            send_mail(subject, message, 'admin@myblog.com', [cd['to']])
            sent = True

            # ! в отличие от книги, я использую флеш-сообщения, а не отображаю сообщение "всё отправлено" в template
            messages.add_message(
                request,
                messages.SUCCESS,
                '"{}" was successfully sent to {}'.format(post.title, cd['to']))

            # и поэтому редирекчу на страницу списка
            return redirect(reverse('blog:post_list'))
    else:
        form = EmailPostForm()

    return render(request, 'blog/post/share.html', {'post': post,
                                                    'form': form})


def post_search(request):
    context = {'form': SearchForm()}

    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            cd = form.cleaned_data
            results = SearchQuerySet().models(Post)\
                      .filter(content=cd['query']).load_all()
            context = {'form': form, 'cd': cd, 'results': results}

    return render(request, 'blog/post/search.html', context)
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import cgi
import models
import logging

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

class WUser( db.Model ):
    username        = db.StringProperty()
    email           = db.EmailProperty()
    
    def user_id( self ):
        return self.key()

class MyPage( webapp.RequestHandler ):
    def GenerateGreeting( self ):
        user = users.get_current_user()
        
        if user:
            muser = _get_or_create_user( user )
            return "<li><a href='/profile'>%s</a></li><li><a href='%s'>My List</a></li><li><a href='%s'>Log Out</a></li>" % (muser.username, self.get_user_item_url( user.user_id()), users.create_logout_url(self.request.uri) )
        else:
            return "<li><a href='%s'>Log In</a></li>" % users.create_login_url(self.request.uri) 

    def PrepItemTemplate( self, items ):
        #ID is not automatically inserted
        for it in items:
            it.id = it.key().id()
            muser = _get_user_by_id( it.owner )
            if( muser ):
                it.username = muser.username
            else:
                it.username = "Anonymous"
    #self.tag_strings = it.get_tag_strings()
    
    def get_item_url(self, item):
        return "/item/%s/%s" % (item.key().id(), cgi.escape(item.title))
    
    def get_user_item_url( self, user_id ):
        if( user_id == -1 ):
            return "/items"
        else:
            return "/items/%s" % user_id
    
def _get_or_create_user(user):
    u = WUser.get_by_key_name(user.user_id())
    if u is None:
        u = WUser(key_name=user.user_id(), email=user.email())
    return u

def _get_user_by_id(user_id):
    u = WUser.get_by_key_name(user_id)
    return u

def _get_current_user(users):
    user = users.get_current_user()
    if user:
        return _get_or_create_user( user )
    return None


class ItemHandler( MyPage ):
    def get( self, item_id, title ):
        user = users.get_current_user()
        greeting = self.GenerateGreeting()
        my_item = models.get_item( long(item_id) )
        
        parent_url = self.get_user_item_url( my_item.owner )
        
        # Initialize whether this item can be edited by the current user
        user_can_edit = None;
        username = None;
        if( user ):
            user_can_edit = ( my_item.owner == user.user_id() )
        
        # Get the username for the user who owns this item
        muser = _get_user_by_id( my_item.owner )
                
        # Output
        template_values = { 'item':my_item, 'greeting':greeting, 'user_can_edit':user_can_edit, 'parent_url':parent_url, 'username':muser.username }
        path = os.path.join( os.path.dirname( __file__ ), 'templates/view_item.htm' )
        self.response.out.write( template.render( path, template_values ) )
    def post( self, item_id, title ):
        user = users.get_current_user()
        
        old_item = models.get_item( long(item_id) )
        if( old_item ):
            if old_item.update( user,
                                self.request.get( "title" ),
                                self.request.get( "comment" ),
                                self.request.get( "tags" ),
                                self.request.get( "problem" ) ):                            
                self.redirect( self.get_item_url( old_item ) )
                return
        
        template_values = {}
        path = os.path.join( os.path.dirname( __file__ ), 'templates/error.htm' )
        self.response.out.write( template.render( path, template_values ) )



class ViewItems( MyPage ):
    def get(self, user_id = -1):
        greeting    = self.GenerateGreeting()
        user        = users.get_current_user()
        
        if user_id == -1 and user:
            user_id = user.user_id();
                
        items = models.get_user_items( user_id )
    
        self.PrepItemTemplate( items )
        
        muser = _get_user_by_id( user_id )
        template_values = {'user':user, 'user_id':user_id, 'items':items, 'greeting':greeting, 'username': muser.username }
        
        path = os.path.join( os.path.dirname( __file__ ), 'templates/view_items.htm' )
        self.response.out.write( template.render( path, template_values ) )

class AddItem( MyPage ):
    def get( self ):
        greeting = self.GenerateGreeting()
        
        
        muser = _get_current_user( users )
        user_id = -1
        if( muser ):
            user_id = muser.user_id();
        parent_url = self.get_user_item_url( user_id )

        template_values = {'greeting':greeting, 'parent_url':parent_url, 'username':muser.username }
        path = os.path.join( os.path.dirname( __file__ ), 'templates/add_new_item.htm' )
        self.response.out.write( template.render( path, template_values ) )
    
    def post( self ):
        models.add_item( 
            users.get_current_user().user_id(), 
            self.request.get( 'title' ),
            self.request.get( "comment" ),
            self.request.get( "tags" ),
            self.request.get( "problem" ) )
        self.redirect( '/items' )

class MainHandler( MyPage):
    def get(self):
        # Handle the pagination
        page = int(self.request.get( 'p', '0' ))
        if page is None:
            page = 0

        items, next = models.get_paged_items( page )
        if next:
            nexturi = "/?p=%d" % (page + 1)
        else:
            nexturi = None
        
        if page > 1:
            prevuri = "/?p=%d" % (page - 1)
        elif page == 1:
            prevuri = "/"
        else:
            prevuri = None
        
        
        greeting = self.GenerateGreeting()
        self.PrepItemTemplate( items )
        user = users.get_current_user()
        if user:
            muser = _get_or_create_user( user )
            if( muser.username is None ):
                self.redirect( '/profile' )
                return
        user_items_url = '/items'
        if( user ):
            user_items_url = '/items/%s' % user.user_id()
        
        tags = models.get_all_tags()
                
                
        template_values = {'greeting':greeting, 'items':items, 'user_items_url':user_items_url,
                            'prevuri':prevuri, 'nexturi':nexturi, 'page':page + 1, 'tags':tags }
        path = os.path.join( os.path.dirname( __file__ ), 'templates/home2.htm' )
        self.response.out.write( template.render( path, template_values ) )

class ProfileHandler( MyPage ):
    def get( self ):
        user = _get_current_user( users )
        greeting = self.GenerateGreeting()
        if user is None:
            self.redirect( '/' )
            return
        
        template_vars = {'greeting':greeting, 'username':user.username}
        path = os.path.join( os.path.dirname( __file__ ), 'templates/profile.htm' )
        self.response.out.write( template.render( path, template_vars ) )
    def post( self ):
        user = _get_current_user(users)
        user.username = self.request.get( 'username' )
        user.put()
        self.redirect( '/' )
        

def main():
    logging.getLogger().setLevel(logging.DEBUG)
    application = webapp.WSGIApplication([('/', MainHandler),
                                          ('/items', ViewItems ),
                                          ('/items/add', AddItem ),
                                          ('/items/(.*)', ViewItems ),
                                          ('/item/(.*)/(.*)', ItemHandler ),
                                          ('/profile', ProfileHandler )
                                          ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()

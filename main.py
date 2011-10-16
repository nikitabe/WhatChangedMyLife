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

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

class Item(db.Model):
    date_submitted  = db.DateTimeProperty(auto_now_add=True)
    comment         = db.TextProperty()
    owner           = db.StringProperty( required=True)
    title           = db.StringProperty( required=True)
    priority        = db.IntegerProperty()
    problem         = db.StringProperty()
    tags            = db.StringProperty()

class WUser( db.Model ):
    username        = db.StringProperty()

class MyPage( webapp.RequestHandler ):
    def GenerateGreeting( self ):
        user = users.get_current_user()
        
        if user:
            muser = _get_or_create_user( user )
            return "%s | <a class='user' href='/profile'>Profile</a> | <a class='user' href='%s'>Log Out</a>" % (muser.username, users.create_logout_url(self.request.uri) )
        else:
            return "<a class='user' href='%s'>Log In</a>" % users.create_login_url(self.request.uri) 
    
    def PrepItemTemplate( self, items ):
        #ID is not automatically inserted
        for it in items:
            it.id = it.key().id()
    
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
        u = WUser(key_name=user.user_id())
    return u

def _get_or_create_user_by_id(user_id):
    u = WUser.get_by_key_name(user_id)
    if u is None:
        u = WUser(key_name=user_id)
    return u


class ItemHandler( MyPage ):
    def get( self, item_id, title ):
        user = users.get_current_user()
        greeting = self.GenerateGreeting()
        my_item = Item.get_by_id( long(item_id) )
        
        parent_url = self.get_user_item_url( my_item.owner )
        
        # Initialize whether this item can be edited by the current user
        user_can_edit = None;
        username = None;
        if( user ):
            user_can_edit = ( my_item.owner == user.user_id() )
        
        # Get the username for the user who owns this item
        muser = _get_or_create_user_by_id( my_item.owner )
                
        # Output
        template_values = { 'item':my_item, 'greeting':greeting, 'user_can_edit':user_can_edit, 'parent_url':parent_url, 'username':muser.username }
        path = os.path.join( os.path.dirname( __file__ ), 'templates/view_item.htm' )
        self.response.out.write( template.render( path, template_values ) )
    def post( self, item_id, title ):
        user = users.get_current_user()
        
        old_item = Item.get_by_id( long(item_id) )
        if( old_item ):
            # check that we can edit this item
            if( old_item.owner == user.user_id() ):
                old_item.title      = self.request.get( "title" )
                old_item.comment    = self.request.get( "comment" )
                old_item.tags       = self.request.get( "tags" );
                old_item.problem    = self.request.get( "problem" );

                old_item.put()
                self.redirect( self.get_item_url( old_item ) )
                return
        template_values = {}
        path = os.path.join( os.path.dirname( __file__ ), 'templates/error.htm' )
        self.response.out.write( template.render( path, template_values ) )



class ViewItems( MyPage ):
    def get(self, user_id = -1):
        greeting = self.GenerateGreeting()
        user = users.get_current_user()
        
        
        if user_id == -1 and user:
            user_id = user.user_id();
        
        items = Item.gql('Where owner = :1 ORDER BY priority DESC', user_id ).fetch( 100 )     
        
        self.PrepItemTemplate( items )
        
        muser = _get_or_create_user_by_id( user_id )
        template_values = {'user':user, 'user_id':user_id, 'items':items, 'greeting':greeting, 'username': muser.username}
        
        path = os.path.join( os.path.dirname( __file__ ), 'templates/view_items.htm' )
        self.response.out.write( template.render( path, template_values ) )

class AddItem( MyPage ):
    def get( self ):
        greeting = self.GenerateGreeting()
        
        user = users.get_current_user()
        muser = _get_or_create_user( user )
        user_id = -1
        if( user ):
            user_id = user.user_id();
        parent_url = self.get_user_item_url( user_id )

        template_values = {'greeting':greeting, 'parent_url':parent_url, 'username':muser.username }
        path = os.path.join( os.path.dirname( __file__ ), 'templates/add_new_item.htm' )
        self.response.out.write( template.render( path, template_values ) )
    
    def post( self ):
        my_item = Item( owner=users.get_current_user().user_id(),
                       title = self.request.get( 'title' ),
                       priority = 1
                       )
        my_item.comment = self.request.get( "comment" );
        my_item.tags    = self.request.get( "tags" );
        my_item.problem = self.request.get( "problem" );
        my_item.put()
        self.redirect( '/items' )

class MainHandler( MyPage):
    def get(self):
        greeting = self.GenerateGreeting()
        items = Item.gql('ORDER BY priority DESC' ).fetch( 100 )     
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
        
        template_values = {'greeting':greeting, 'items':items, 'user_items_url':user_items_url}
        path = os.path.join( os.path.dirname( __file__ ), 'templates/home.htm' )
        self.response.out.write( template.render( path, template_values ) )

class ProfileHandler( MyPage ):
    def get( self ):
        user = users.get_current_user()
        greeting = self.GenerateGreeting()
        if user is None:
            self.redirect( '/' )
            return
        our_user = _get_or_create_user(user)
        
        template_vars = {'greeting':greeting, 'username':our_user.username}
        path = os.path.join( os.path.dirname( __file__ ), 'templates/profile.htm' )
        self.response.out.write( template.render( path, template_vars ) )
    def post( self ):
        user = users.get_current_user()
        muser = _get_or_create_user( user )
        muser.username = self.request.get( 'username' )
        muser.put()
        self.redirect( '/' )
        

def main():
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

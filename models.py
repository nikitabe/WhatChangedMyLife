import logging
import string
from google.appengine.ext import db
from google.appengine.api import users

PAGE_SIZE = 5

class Tag( db.Model ):
    #name  is going to be the key    = db.StringProperty()
    name = db.StringProperty()
    deleted     = db.BooleanProperty( default=False)

class Item(db.Model):
    date_submitted  = db.DateTimeProperty(auto_now_add=True)
    comment         = db.TextProperty()
    owner           = db.StringProperty( required=True)
    title           = db.StringProperty( required=True)
    priority        = db.IntegerProperty()
    problem         = db.StringProperty()
    tags            = db.StringProperty()  # old way as a string
    tags_list       = db.ListProperty(db.Key) #new way as references
    deleted         = db.BooleanProperty( default=False)
    
    def update( self, user, title, comment, tags, problem ):
        
        # check that we can edit this item
        if( self.owner == user.user_id() ):
            
            ts = TagItem.gql( "where deleted = false and item = :1", self.key() )
            for t in ts:
                t.deleted = True
                t.put()
                 
            self.title      = title
            self.comment    = comment
            self.tags       = tags
            self.problem    = problem
            
            new_tags = string.split( tags, ",")
            for t in new_tags:
                t = t.strip()
                tag_item = Tag.get_or_insert( key_name=t )
                tag_item.name=t
                tag_item.put() # Is this necessary?  Can I do without this?     
                    
                ti = TagItem()
                ti.item = self
                ti.tag = tag_item
                ti.put()
                 
            self.put()
            return True
        return false

#def get_tag_strings(self):
        
        

class TagItem( db.Model ):
    tag         = db.ReferenceProperty( Tag, collection_name="tags" )
    item        = db.ReferenceProperty( Item, collection_name="items" )
    deleted     = db.BooleanProperty( default=False)


def get_item( id ):
    return Item.get_by_id( id )

def get_user_items( user_id ):
    return Item.gql('Where owner = :1 ORDER BY date_submitted DESC', user_id ).fetch( 1000 )

def get_all_items( offset=None ):
    return Item.gql('ORDER BY priority DESC' ).fetch( 100 )

def get_paged_items( page=0 ):
    extra = None
    items = Item.gql('ORDER BY __key__ DESC').fetch(PAGE_SIZE+1, page*PAGE_SIZE )
    if( len(items) > PAGE_SIZE ):
       extra = items[-1]
       items = items[:PAGE_SIZE]
    return items, extra

def add_item( owner_id, title_in, comment, tags, problem ):
    new_item = Item( owner = owner_id,
                   title = title_in,
                   priority = 1
                   )
    new_item.comment = comment;
    new_item.tags    = tags;
    new_item.problem = problem;
    new_item.put()

def get_all_tags():
    tags = Tag.all().fetch(100)
    return tags

def get_items_by_tag( page, tag_str ):
    items = []
    t = Tag.get_or_insert( tag_str )
    # Get all tagitems that reference t
    tis = TagItem.gql( "where deleted = false and tag=:1", t.key() )
    # for all tagitems, add item
    for ti in tis:
        items.append(  Item.get( ti.item.key() ) )
    
    return items, None

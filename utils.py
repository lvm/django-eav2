from django.db.models.signals import post_init, post_save, post_delete
from .managers import EntityManager
from .models import EavEntity, EavAttribute, get_unique_class_identifier

class EavConfig(object):

    proxy_field_name = 'eav'
    manager_field_name ='objects'

    @classmethod
    def get_eav_attributes(cls):
        """
             By default, all attributes apply to an entity,
             unless otherwise specified.
        """
        return EavAttribute.objects.all()
        

class EavRegistry(object):
    """
        Tools to add eav features to models
    """
    cache = {}

    @staticmethod
    def attach(sender, *args, **kwargs):
        """
            Attache EAV toolkit to an instance after init.
        """
        cls_id = get_unique_class_identifier(sender)
        instance = kwargs['instance']
        config_cls = EavRegistry.cache[cls_id]['config_cls']

        setattr(instance, config_cls.proxy_field_name, EavEntity(instance))


    @staticmethod
    def update_attribute_cache(sender, *args, **kwargs):
        """
            Update the attribute cache for all the models every time we
            create an attribute.
        """
        for cache in EavRegistry.cache.itervalues():
            EavEntity.update_attr_cache_for_model(cache['model_cls'])


    @staticmethod
    def register(model_cls, config_cls=EavConfig):
        """
            Inject eav features into the given model and attach a signal 
            listener to it for setup.
        """
        
        cls_id = get_unique_class_identifier(model_cls)
        
        if cls_id in EavRegistry.cache:
            return
        
        post_init.connect(EavRegistry.attach, sender=model_cls)
        post_save.connect(EavEntity.save_handler, sender=model_cls)
        EavRegistry.cache[cls_id] = { 'config_cls': config_cls,
                                                  'model_cls': model_cls } 

        if hasattr(model_cls, config_cls.manager_field_name):
            mgr = getattr(model_cls, config_cls.manager_field_name)
            EavRegistry.cache[cls_id]['old_mgr'] = mgr

        setattr(model_cls, config_cls.proxy_field_name, EavEntity)

        setattr(getattr(model_cls, config_cls.proxy_field_name),
                        'get_eav_attributes', config_cls.get_eav_attributes)

        mgr = EntityManager()
        mgr.contribute_to_class(model_cls, config_cls.manager_field_name)
        
        EavEntity.update_attr_cache_for_model(model_cls)


    @staticmethod
    def unregister(model_cls):
        """
            Inject eav features into the given model and attach a signal 
            listener to it for setup.
        """
        cls_id = get_unique_class_identifier(model_cls)
        
        if not cls_id in EavRegistry.cache:
            return

        cache = EavRegistry.cache[cls_id]
        config_cls = cache['config_cls']
        post_init.disconnect(EavRegistry.attach, sender=model_cls)
        post_save.disconnect(EavEntity.save_handler, sender=model_cls)
        
        try:
            delattr(model_cls, config_cls.manager_field_name)
        except AttributeError:
            pass

        if 'old_mgr' in cache:
            cache['old_mgr'].contribute_to_class(model_cls, 
                                                config_cls.manager_field_name)

        try:
            delattr(model_cls, config_cls.proxy_field_name)
        except AttributeError:
            pass

        EavEntity.flush_attr_cache_for_model(model_cls)
        EavRegistry.cache.pop(cls_id)
        
        
     # todo : test cache
     # todo : tst unique identitfier  
     # todo:  test update attribute cache on attribute creation
     
post_save.connect(EavRegistry.update_attribute_cache, sender=EavAttribute)
post_delete.connect(EavRegistry.update_attribute_cache, sender=EavAttribute)
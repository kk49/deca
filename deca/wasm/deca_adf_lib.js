

mergeInto(LibraryManager.library, {
    db_print: function(offset, sz) {
        const str_raw = new Uint8Array(Module.HEAPU8.buffer, offset, sz);
        const str = new TextDecoder("utf-8").decode(str_raw)
        console.log('db_print:', str);
    },

    db_warn: function(offset, sz) {
        const str_raw = new Uint8Array(Module.HEAPU8.buffer, offset, sz);
        const str = new TextDecoder("utf-8").decode(str_raw)
        console.warn('db_warn:', str);
    },

    db_error: function(offset, sz) {
        const str_raw = new Uint8Array(Module.HEAPU8.buffer, offset, sz);
        const str = new TextDecoder("utf-8").decode(str_raw)
        console.error('db_error:', str);
    },

    dict_push: function() {
        // console.log('dict_push');
        Module.adf_stack.push({});
    },

    dict_field_set: function() {
        // console.log('dict_field_set');
        const v = Module.adf_stack.pop();
        const k = Module.adf_stack.pop();
        let d = Module.adf_stack.pop();
        d[k] = v;
        Module.adf_stack.push(d);
    },

    list_push: function() {
        // console.log('list_push');
        Module.adf_stack.push([]);
    },

    list_append: function() {
        // console.log('list_append');
        const v = Module.adf_stack.pop();
        let l = Module.adf_stack.pop();
        l.push(v);
        Module.adf_stack.push(l);
    },


    hash_register: function(hash, offset, sz) {
        console.log('hash_register', hash, offset, sz);
    },

    hash32_push: function(value) {
        // console.log('hash32_push', hash);
        Module.adf_stack.push(value);
    },

    hash48_push: function(value) {
        // console.log('hash48_push', hash);
        Module.adf_stack.push(value);
    },

    hash64_push: function(value) {
        // console.log('hash64_push', hash);
        Module.adf_stack.push(value);
    },

    bool_push: function(value) {
        // console.log('bool_push', value);
        Module.adf_stack.push(value);
    },

    s8_push: function(value) {
        // console.log('s8_push', value);
        Module.adf_stack.push(value);
    },

    u8_push: function(value) {
        // console.log('u8_push', value);
        Module.adf_stack.push(value);
    },

    s16_push: function(value) {
        // console.log('s16_push', value);
        Module.adf_stack.push(value);
    },

    u16_push: function(value) {
        // console.log('u16_push', value);
        Module.adf_stack.push(value);
    },

    s32_push: function(value) {
        // console.log('s32_push', value);
        Module.adf_stack.push(value);
    },

    u32_push: function(value) {
        // console.log('u32_push', value);
        Module.adf_stack.push(value);
    },

    s64_push: function(value) {
        // console.log('s64_push', value);
        Module.adf_stack.push(value);
    },

    u64_push: function(value) {
        // console.log('u64_push', value);
        Module.adf_stack.push(value);
    },

    f32_push: function(value) {
        // console.log('f32_push', value);
        Module.adf_stack.push(value);
    },

    f64_push: function(value) {
        // console.log('f64_push', value);
        Module.adf_stack.push(value);
    },

    str_push: function(offset, sz) {
        // console.log('str_push', offset, sz);
        const str_raw = new Uint8Array(Module.HEAPU8.buffer, offset, sz);
        const str = new TextDecoder("utf-8").decode(str_raw)
        Module.adf_stack.push(str);
    },

    enum_push: function(value, offset, sz) {
        // console.log('enum_push', offset, sz);
        const str_raw = new Uint8Array(Module.HEAPU8.buffer, offset, sz);
        const str = new TextDecoder("utf-8").decode(str_raw)
        Module.adf_stack.push([value, str]);
    },

    s8s_push: function(offset, cnt) {
        // console.log('s8s_push', offset, cnt);
        Module.adf_stack.push(new Int8Array(Module.HEAPU8.buffer, offset, cnt));
    },

    u8s_push: function(offset, cnt) {
        // console.log('u8s_push', offset, cnt);
        Module.adf_stack.push(new Uint8Array(Module.HEAPU8.buffer, offset, cnt));
    },

    s16s_push: function(offset, cnt) {
        // console.log('s16s_push', offset, cnt);
        Module.adf_stack.push(new Int16Array(Module.HEAPU8.buffer, offset, cnt));
    },

    u16s_push: function(offset, cnt) {
        // console.log('u16s_push', offset, cnt);
        Module.adf_stack.push(new Uint16Array(Module.HEAPU8.buffer, offset, cnt));
    },

    s32s_push: function(offset, cnt) {
        // console.log('s32s_push', offset, cnt);
        Module.adf_stack.push(new Int32Array(Module.HEAPU8.buffer, offset, cnt));
    },

    u32s_push: function(offset, cnt) {
        // console.log('u32s_push', offset, cnt);
        Module.adf_stack.push(new Uint32Array(Module.HEAPU8.buffer, offset, cnt));
    },

    s64s_push: function(offset, cnt) {
        // console.log('s64s_push', offset, cnt);
        Module.adf_stack.push(new BigInt64Array(Module.HEAPU8.buffer, offset, cnt));
    },

    u64s_push: function(offset, cnt) {
        // console.log('u64s_push', offset, cnt);
        Module.adf_stack.push(new BigUint64Array(Module.HEAPU8.buffer, offset, cnt));
    },

    f32s_push: function(offset, cnt) {
        // console.log('f32s_push', offset, cnt);
        Module.adf_stack.push(new Float32Array(Module.HEAPU8.buffer, offset, cnt));
    },

    f64s_push: function(offset, cnt) {
        // console.log('f64s_push', offset, cnt);
        Module.adf_stack.push(new Float64Array(Module.HEAPU8.buffer, offset, cnt));
    },

});
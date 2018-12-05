#ifdef __cplusplus
extern "C" {
#endif

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

int process_image(
    u8 * dst_image_buf,
    u32 dst_image_sz,
    u8 const * src_buffer_buf,
    u32 src_buffer_sz,
    u32 nx,
    u32 ny,
    u32 pixel_format
    )
{

    switch(pixel_format)
    {

        case 10:
            {
                u8 * optr = (u8 *)dst_image_buf;
                u16 const * iptr = (u16 const*)src_buffer_buf;
                //TODO check lengths for buffer overruns
                for(u32 yi = 0; yi < ny; ++yi)
                {
                    for(u32 xi = 0; xi < nx; ++xi)
                    {
                        *optr = *iptr >> 8; optr += 1; iptr += 1;
                        *optr = *iptr >> 8; optr += 1; iptr += 1;
                        *optr = *iptr >> 8; optr += 1; iptr += 1;
                        *optr = *iptr >> 8; optr += 1; iptr += 1;
                    }
                }
                return 0;
            }
            break;
        case 26:
            {
                u8 * optr = (u8 *)dst_image_buf;
                u32 const * iptr = (u32 const*)src_buffer_buf;
                //TODO check lengths for buffer overruns
                for(u32 yi = 0; yi < ny; ++yi)
                {
                    for(u32 xi = 0; xi < nx; ++xi)
                    {
                        optr[0] = ((*iptr >> 21) & 0x07ff) >> 3;
                        optr[1] = ((*iptr >> 10) & 0x07ff) >> 3;
                        optr[2] = ((*iptr >> 0) & 0x03ff) >> 2;
                        optr[3] = 0xFF;
                        optr += 4;
                        iptr += 1;
                    }
                }
                return 0;
            }
            break;
        case 28:
            {
                u8 * optr = dst_image_buf;
                u8 const * iptr = src_buffer_buf;
                //TODO check lengths for buffer overruns
                for(u32 yi = 0; yi < ny; ++yi)
                {
                    for(u32 xi = 0; xi < nx; ++xi)
                    {
                        optr[0] = iptr[0];
                        optr[1] = iptr[1];
                        optr[2] = iptr[2];
                        optr[3] = iptr[3];
                        optr += 4;
                        iptr += 4;
                    }
                }
                return 0;
            }
            break;
        case 87:
            {
                u8 * optr = dst_image_buf;
                u8 const * iptr = src_buffer_buf;
                //TODO check lengths for buffer overruns
                for(u32 yi = 0; yi < ny; ++yi)
                {
                    for(u32 xi = 0; xi < nx; ++xi)
                    {
                        optr[0] = iptr[2];
                        optr[1] = iptr[1];
                        optr[2] = iptr[0];
                        optr[3] = iptr[3];
                        optr += 4;
                        iptr += 4;
                    }
                }
                return 0;
            }
            break;
        case 71:
            {
                if(nx < 4) nx = 4;
                if(ny < 4) ny = 4;
                u32 bnx = nx >> 2;
                u32 bny = ny >> 2;
                u8 const * iptr = src_buffer_buf;
                for(u32 yo = 0; yo < bny; ++yo)
                {
                    for(u32 xo = 0;  xo < bnx; ++xo)
                    {
                        u16 color0 = *((u16 const*)(iptr + 0));
                        u16 color1 = *((u16 const*)(iptr + 2));
                        u32 cidx = *((u32 const*)(iptr + 4));
                        iptr += 8;

                        u8 colors8[16];
                        u32 const* colors = (u32 const*)colors8;

                        colors8[0*4 + 0] = ((color0 >> 11) & 0x1F) << 3;
                        colors8[0*4 + 1] = ((color0 >>  5) & 0x3F) << 2;
                        colors8[0*4 + 2] = ((color0 >>  0) & 0x1F) << 3;
                        colors8[0*4 + 3] = 0xFF;
                        colors8[1*4 + 0] = ((color1 >> 11) & 0x1F) << 3;
                        colors8[1*4 + 1] = ((color1 >>  5) & 0x3F) << 2;
                        colors8[1*4 + 2] = ((color1 >>  0) & 0x1F) << 3;
                        colors8[1*4 + 3] = 0xFF;

                        if(color0 > color1)
                        {
                            for(u32 i = 0; i < 3; ++i)
                            {
                                colors8[2*4 + i] = (2 * (u16)colors8[0*4 + i] + (u16)colors8[1*4 + i]) / 3;
                                colors8[3*4 + i] = ((u16)colors8[0*4 + i] + 2 * (u16)colors8[1*4 + i]) / 3;
                            }
                            colors8[2*4 + 3] = 0xFF;
                            colors8[3*4 + 3] = 0xFF;
                        }
                        else
                        {
                            for(u32 i = 0; i < 3; ++i)
                            {
                                colors8[2*4 + i] = (colors8[0*4 + i] + colors8[1*4 + i]) >> 1;
                            }
                            colors8[2*4 + 3] = 0xFF;

                            colors[3] = 0;
                        }

                        for(u32 yi = 0; yi < 4; ++yi)
                        {
                            u8 * optr = dst_image_buf;
                            optr += xo * 4 * 4;  // block offset in X
                            optr += yo * 4 * 4 * nx; // block offset in Y
                            optr += yi * 4 * nx; // pixel offset in Y
                            for(u32 xi = 0; xi < 4; ++xi)
                            {
                                *((u32*)optr) = colors[cidx & 0x3];
                                cidx = cidx >> 2;
                                optr += 4;
                            }
                        }
                    }
                }
                return 0;
            }
            break;
        default:
            return -1; // FORMAT NOT HANDLED
    }
    return -2; //OTHER ERROR
}

#ifdef __cplusplus
}
#endif

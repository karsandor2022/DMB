const { QueryType } = require('discord-player');
const getButtons = require('../../utils/buttons');
const getProgressBar = require('../../utils/progressbar');

module.exports = {
    name: 'play',
    description: 'Play music with interactive dashboard',
    options: [{ name: 'query', type: 3, description: 'Song name or URL', required: true }],
    async execute(client, interaction) {
        const query = interaction.options?.getString('query') || interaction.fields?.getTextInputValue('song_input');
        const channel = interaction.member.voice.channel;

        if (!channel) return interaction.reply({ content: "❌ Join Voice Channel!", ephemeral: true });
        if (interaction.isChatInputCommand()) await interaction.deferReply();

        const buttons = getButtons();

        // LOCAL MODE
        if (client.mode === 'LOCAL') {
            try {
                const res = await client.player.search(query, {
                    requestedBy: interaction.user,
                    searchEngine: QueryType.AUTO
                });
                if (!res || !res.tracks.length) return interaction.editReply("❌ No results.");

                const { track } = await client.player.play(channel, res, {
                    nodeOptions: { 
                        metadata: interaction,
                        volume: client.defaultVolume // USES YOUR CONFIG VOLUME
                    }
                });

                const bar = getProgressBar(0, track.durationMS);
                const msg = { content: `🎵 **Playing:** ${track.title}\n${bar}`, components: buttons };
                
                if (interaction.isChatInputCommand()) await interaction.editReply(msg);
                else await interaction.reply(msg);
            } catch (e) {
                console.error(e);
            }
        } 
        // REMOTE MODE (Lavalink)
        else {
            const node = client.shoukaku.getNode();
            const res = await node.rest.resolve(query) || await node.rest.resolve(`ytsearch:${query}`);
            if (!res || !res.tracks.length) return interaction.editReply("❌ No results.");
            const track = res.tracks[0];

            let player = node.players.get(interaction.guild.id);
            if (!player) player = await node.joinChannel({ guildId: interaction.guild.id, channelId: channel.id, shardId: 0 });

            player.playTrack({ track: track.encoded });
            player.setGlobalVolume(client.defaultVolume); // USES YOUR CONFIG VOLUME

            const bar = getProgressBar(0, track.info.length);
            const msg = { content: `🎵 **Playing:** ${track.info.title}\n${bar}`, components: buttons };
            
            if (interaction.isChatInputCommand()) await interaction.editReply(msg);
            else await interaction.reply(msg);
        }
    }
};